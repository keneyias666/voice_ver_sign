"""
Server-side text-to-speech using pyttsx3 (offline). Falls back gracefully if unavailable.
"""
from __future__ import annotations

import base64
import os
import tempfile
import threading
from typing import Optional

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None  # type: ignore[assignment,misc]

_tts_lock = threading.Lock()


def synthesize_speech_base64(text: str) -> Optional[str]:
    """Return WAV audio as base64, or None if TTS is unavailable."""
    cleaned = (text or "").strip()
    if not cleaned or pyttsx3 is None:
        return None

    tmp_path = None
    try:
        with _tts_lock:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            engine.save_to_file(cleaned, tmp_path)
            engine.runAndWait()
            engine.stop()

        with open(tmp_path, "rb") as audio_file:
            data = audio_file.read()
        if not data:
            return None
        return base64.b64encode(data).decode("ascii")
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
