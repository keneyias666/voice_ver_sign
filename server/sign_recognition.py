"""
Sign language recognition from webcam frames.

Uses MediaPipe Hand Landmarker for landmark extraction and rule-based classification
for ASL fingerspelling (A–Z) plus common one-hand signs (hello, yes, no, etc.).
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import cv2
import mediapipe as mp
import numpy as np

_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"

# Landmark indices (MediaPipe Hands)
_WRIST = 0
_THUMB_TIP, _THUMB_IP, _THUMB_MCP = 4, 3, 2
_INDEX_TIP, _INDEX_PIP, _INDEX_MCP = 8, 6, 5
_MIDDLE_TIP, _MIDDLE_PIP, _MIDDLE_MCP = 12, 10, 9
_RING_TIP, _RING_PIP, _RING_MCP = 16, 14, 13
_PINKY_TIP, _PINKY_PIP, _PINKY_MCP = 20, 18, 17

_FINGERSPELLING = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


@dataclass(frozen=True)
class FingerState:
    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool

    @property
    def extended_count(self) -> int:
        return sum((self.thumb, self.index, self.middle, self.ring, self.pinky))

    def as_tuple(self) -> tuple[bool, bool, bool, bool, bool]:
        return (self.thumb, self.index, self.middle, self.ring, self.pinky)


@dataclass(frozen=True)
class RecognitionResult:
    text: str
    confidence: float
    message: str
    hands_detected: int = 0
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "message": self.message,
            "handsDetected": self.hands_detected,
            "label": self.label,
        }


@lru_cache(maxsize=1)
def _hands_detector():
    if not _MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Missing MediaPipe model at {_MODEL_PATH}. "
            "Download hand_landmarker.task from Google MediaPipe models."
        )
    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(_MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.15,
        min_hand_presence_confidence=0.15,
        min_tracking_confidence=0.15,
    )
    return mp.tasks.vision.HandLandmarker.create_from_options(options)


def _apply_gamma(frame_bgr: np.ndarray, gamma: float) -> np.ndarray:
    inv_gamma = 1.0 / max(gamma, 0.1)
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(frame_bgr, table)


def _resize_for_detection(frame_bgr: np.ndarray) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    target = 640
    if width <= target:
        return frame_bgr
    scale = target / float(width)
    return cv2.resize(frame_bgr, (target, int(height * scale)), interpolation=cv2.INTER_AREA)


def enhance_frame_for_detection(frame_bgr: np.ndarray) -> np.ndarray:
    """Boost dark / low-contrast webcam frames so MediaPipe can find hands."""
    frame_bgr = _resize_for_detection(frame_bgr)
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    enhanced = cv2.cvtColor(cv2.merge([l_channel, a_channel, b_channel]), cv2.COLOR_LAB2BGR)

    mean_brightness = float(np.mean(enhanced))
    if mean_brightness < 60:
        # Very dark: extreme boost
        enhanced = cv2.convertScaleAbs(enhanced, alpha=2.5, beta=80)
        enhanced = _apply_gamma(enhanced, 2.5)
    elif mean_brightness < 90:
        enhanced = cv2.convertScaleAbs(enhanced, alpha=2.0, beta=60)
        enhanced = _apply_gamma(enhanced, 2.0)
    elif mean_brightness < 130:
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.65, beta=45)
        enhanced = _apply_gamma(enhanced, 1.5)
    return enhanced


def _enhance_extreme(frame_bgr: np.ndarray) -> np.ndarray:
    """Maximum brightness boost for extremely dark frames."""
    frame = _resize_for_detection(frame_bgr)
    # Massive linear boost first
    frame = cv2.convertScaleAbs(frame, alpha=3.0, beta=100)
    # Aggressive gamma
    frame = _apply_gamma(frame, 3.0)
    # Denoise to reduce artifacts from extreme boosting
    frame = cv2.fastNlMeansDenoisingColored(frame, None, 8, 8, 7, 21)
    return frame


def _enhance_histogram_eq(frame_bgr: np.ndarray) -> np.ndarray:
    """Histogram equalization per channel for maximum contrast."""
    frame = _resize_for_detection(frame_bgr)
    # Convert to YCrCb and equalize the Y (luminance) channel
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y = cv2.equalizeHist(y)
    equalized = cv2.cvtColor(cv2.merge([y, cr, cb]), cv2.COLOR_YCrCb2BGR)
    # Additional brightness boost if still dark
    mean_b = float(np.mean(equalized))
    if mean_b < 120:
        equalized = cv2.convertScaleAbs(equalized, alpha=1.8, beta=50)
    return equalized


def decode_frame(image_base64: str) -> Optional[np.ndarray]:
    if not image_base64:
        return None
    try:
        raw = base64.b64decode(image_base64)
    except (ValueError, binascii.Error):
        return None
    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def _lm_xy(landmarks, idx: int) -> np.ndarray:
    pt = landmarks[idx]
    return np.array([pt.x, pt.y], dtype=np.float32)


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _finger_extended(landmarks, tip: int, pip: int, wrist: int) -> bool:
    tip_pt = _lm_xy(landmarks, tip)
    pip_pt = _lm_xy(landmarks, pip)
    wrist_pt = _lm_xy(landmarks, wrist)
    # Relaxed from 1.03 to 1.01 to be more tolerant of hand tilt
    return _dist(tip_pt, wrist_pt) > _dist(pip_pt, wrist_pt) * 1.01


def _thumb_extended(landmarks) -> bool:
    tip = _lm_xy(landmarks, _THUMB_TIP)
    ip = _lm_xy(landmarks, _THUMB_IP)
    mcp = _lm_xy(landmarks, _THUMB_MCP)
    wrist = _lm_xy(landmarks, _WRIST)
    index_mcp = _lm_xy(landmarks, _INDEX_MCP)
    # Relaxed multipliers to improve thumb gesture detection sensitivity
    if _dist(tip, wrist) > _dist(ip, wrist) * 1.0:
        return True
    if _dist(tip, mcp) > _dist(ip, mcp) * 1.02:
        return True
    return _dist(tip, index_mcp) > _dist(ip, index_mcp) * 1.01


def get_finger_states(landmarks) -> FingerState:
    wrist = _WRIST
    return FingerState(
        thumb=_thumb_extended(landmarks),
        index=_finger_extended(landmarks, _INDEX_TIP, _INDEX_PIP, wrist),
        middle=_finger_extended(landmarks, _MIDDLE_TIP, _MIDDLE_PIP, wrist),
        ring=_finger_extended(landmarks, _RING_TIP, _RING_PIP, wrist),
        pinky=_finger_extended(landmarks, _PINKY_TIP, _PINKY_PIP, wrist),
    )


def _fingertips_close(landmarks, tip_indices: Iterable[int], threshold: float = 0.08) -> bool:
    # Calculate hand size (distance from wrist to middle MCP)
    wrist_pt = _lm_xy(landmarks, _WRIST)
    middle_mcp = _lm_xy(landmarks, _MIDDLE_MCP)
    hand_size = max(float(_dist(wrist_pt, middle_mcp)), 0.01)
    
    # Scale threshold relative to typical hand_size (approx 0.20)
    scaled_threshold = (threshold / 0.20) * hand_size
    
    tips = [_lm_xy(landmarks, i) for i in tip_indices]
    dists = [_dist(tips[i], tips[j]) for i in range(len(tips)) for j in range(i + 1, len(tips))]
    return bool(dists) and max(dists) < scaled_threshold


def _is_l_shape(landmarks) -> bool:
    thumb_tip = _lm_xy(landmarks, _THUMB_TIP)
    index_tip = _lm_xy(landmarks, _INDEX_TIP)
    index_mcp = _lm_xy(landmarks, _INDEX_MCP)
    thumb_index = _dist(thumb_tip, index_tip)
    index_len = _dist(index_tip, index_mcp)
    
    # Calculate hand size
    wrist_pt = _lm_xy(landmarks, _WRIST)
    middle_mcp = _lm_xy(landmarks, _MIDDLE_MCP)
    hand_size = max(float(_dist(wrist_pt, middle_mcp)), 0.01)
    
    # Scale threshold relative to typical hand_size (approx 0.20)
    scaled_index_len_threshold = (0.04 / 0.20) * hand_size
    return thumb_index > index_len * 0.55 and index_len > scaled_index_len_threshold


def classify_landmarks(landmarks) -> tuple[str, float, str]:
    """Return (display_text, confidence, internal_label)."""
    fs = get_finger_states(landmarks)
    t, i, m, r, p = fs.as_tuple()

    # Calculate hand size for distance-independent thresholds
    wrist_pt = _lm_xy(landmarks, _WRIST)
    middle_mcp = _lm_xy(landmarks, _MIDDLE_MCP)
    hand_size = max(float(_dist(wrist_pt, middle_mcp)), 0.01)

    # ASL "O" check: fingers are curled, and tips are close to each other AND to the thumb tip.
    if not i and not m and not r and not p:
        if _fingertips_close(landmarks, (_INDEX_TIP, _MIDDLE_TIP, _RING_TIP, _PINKY_TIP)):
            thumb_tip = _lm_xy(landmarks, _THUMB_TIP)
            index_tip = _lm_xy(landmarks, _INDEX_TIP)
            middle_tip = _lm_xy(landmarks, _MIDDLE_TIP)
            scaled_o_thumb_threshold = (0.085 / 0.20) * hand_size
            if _dist(index_tip, thumb_tip) < scaled_o_thumb_threshold and _dist(middle_tip, thumb_tip) < scaled_o_thumb_threshold:
                return ("O", 0.82, "letter_o")

    if t and i and not m and not r and p:
        return ("I love you", 0.88, "love")

    if i and m and not r and not p and not t:
        return ("V", 0.84, "letter_v")

    if i and m and r and not p and not t:
        return ("W / Water", 0.83, "letter_w")

    if t and p and not i and not m and not r:
        return ("Y", 0.8, "letter_y")

    if p and not i and not m and not r and not t:
        return ("I", 0.8, "letter_i")

    if t and i and not m and not r and not p and _is_l_shape(landmarks):
        return ("L", 0.85, "letter_l")

    # ASL "No" gesture (index + middle tips close to thumb tip, ring & pinky folded)
    thumb_tip = _lm_xy(landmarks, _THUMB_TIP)
    index_tip = _lm_xy(landmarks, _INDEX_TIP)
    middle_tip = _lm_xy(landmarks, _MIDDLE_TIP)
    scaled_no_threshold = (0.085 / 0.20) * hand_size
    if _dist(index_tip, thumb_tip) < scaled_no_threshold and _dist(middle_tip, thumb_tip) < scaled_no_threshold and not r and not p:
        return ("No", 0.85, "no")

    if t and not i and not m and not r and not p:
        return ("Yes", 0.86, "yes")

    if t and i and m and r and p:
        return ("Hello", 0.8, "hello")

    if not t and i and m and r and p:
        return ("B", 0.78, "letter_b")

    if not t and not i and m and not r and not p:
        return ("Please", 0.7, "please")

    if not t and i and not m and not r and not p:
        return ("Help", 0.74, "help")

    if fs.extended_count == 0:
        thumb_tip = _lm_xy(landmarks, _THUMB_TIP)
        index_mcp = _lm_xy(landmarks, _INDEX_MCP)
        wrist_pt = _lm_xy(landmarks, _WRIST)
        if _dist(thumb_tip, wrist_pt) > _dist(index_mcp, wrist_pt) * 0.85:
            return ("A", 0.76, "letter_a")
        return ("Sorry", 0.75, "sorry")

    return ("", 0.0, "unknown")


def classify_two_hands(primary, secondary) -> tuple[str, float, str]:
    text, conf, label = classify_landmarks(primary)
    if text:
        return text, conf, label
    _, _, sec_label = classify_landmarks(secondary)
    if sec_label != "unknown":
        return classify_landmarks(secondary)
    return ("Help", 0.7, "help_two_hands")


def extract_hand_landmarks(frame_bgr: np.ndarray) -> list:
    detector = _hands_detector()
    # Try multiple enhancement strategies — dark webcams need aggressive boosting
    candidates = [
        enhance_frame_for_detection(frame_bgr),  # CLAHE + adaptive boost
        frame_bgr,                                 # Original (works if lighting is fine)
        _enhance_histogram_eq(frame_bgr),          # Histogram equalization
        _enhance_extreme(frame_bgr),               # Nuclear option for very dark frames
    ]
    for frame in candidates:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)
        if result.hand_landmarks:
            return list(result.hand_landmarks)
    return []


def recognize_sign_from_frame(image_base64: str) -> dict:
    frame = decode_frame(image_base64)
    if frame is None:
        return RecognitionResult("", 0.0, "Invalid or empty image data.").to_dict()

    # Debug: Save frames to look at what is being received and processed
    try:
        cv2.imwrite("debug_original.png", frame)
        cv2.imwrite("debug_enhanced.png", enhance_frame_for_detection(frame))
        cv2.imwrite("debug_hist_eq.png", _enhance_histogram_eq(frame))
        cv2.imwrite("debug_extreme.png", _enhance_extreme(frame))
    except Exception:
        pass

    hands = extract_hand_landmarks(frame)
    if not hands:
        return RecognitionResult("", 0.0, "No hand detected — center your sign in the camera.", 0).to_dict()

    if len(hands) >= 2:
        text, confidence, label = classify_two_hands(hands[0], hands[1])
    else:
        text, confidence, label = classify_landmarks(hands[0])

    if not text:
        return RecognitionResult(
            "",
            0.0,
            "Hand detected — hold a clear sign (try Yes, Hello, I love you, or fingerspell A–Z).",
            len(hands),
            label,
        ).to_dict()

    return RecognitionResult(
        text,
        confidence,
        f"Recognized “{text}” ({int(confidence * 100)}% confidence).",
        len(hands),
        label,
    ).to_dict()


def recognize_sign_from_frames(frames: list[str]) -> dict:
    if not frames:
        return RecognitionResult("", 0.0, "No frames received.").to_dict()

    votes: dict[str, float] = {}
    votes_count: dict[str, int] = {}
    messages: dict[str, str] = {}
    hands_max = 0
    frames_with_hands = 0

    for frame_b64 in frames:
        if not frame_b64 or len(frame_b64) < 50:
            continue
        result = recognize_sign_from_frame(frame_b64)
        detected = int(result.get("handsDetected") or 0)
        hands_max = max(hands_max, detected)
        if detected > 0:
            frames_with_hands += 1
        text = (result.get("text") or "").strip()
        if not text:
            continue
        conf = float(result.get("confidence") or 0)
        votes[text] = votes.get(text, 0.0) + conf
        votes_count[text] = votes_count.get(text, 0) + 1
        messages[text] = result.get("message") or ""

    if not votes:
        if frames_with_hands > 0:
            return RecognitionResult(
                "",
                0.0,
                f"Hand tracked on {frames_with_hands} frame(s) — hold Yes (thumb up) or Hello (open palm) steady.",
                hands_max,
            ).to_dict()
        return RecognitionResult(
            "",
            0.0,
            "No hand detected — move closer, add light, and center your hand in the frame.",
            hands_max,
        ).to_dict()

    best_text = max(votes, key=lambda label: votes[label])
    # Average confidence over the frames where this specific sign was successfully detected
    avg_conf = votes[best_text] / max(1, votes_count[best_text])
    avg_conf = min(avg_conf, 1.0)

    return RecognitionResult(
        best_text,
        avg_conf,
        messages.get(best_text) or f"Recognized “{best_text}” from {len(frames)} frames.",
        hands_max,
    ).to_dict()
