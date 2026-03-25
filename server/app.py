"""
Voice2Sign – FastAPI backend.
Single server that provides API endpoints and serves the frontend.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ConfigDict

from . import database as db
from . import auth
from . import config

# ── Pydantic Models ──

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    userType: str = "hearing"

class ForgotPasswordRequest(BaseModel):
    email: str

class InputToggleRequest(BaseModel):
    active: bool

class CreateChatRequest(BaseModel):
    title: str = "New conversation"

class SendMessageRequest(BaseModel):
    content: str

class PreferencesRequest(BaseModel):
    data: dict = {}


class PipelineSignRecognizeRequest(BaseModel):
    """Frame from webcam — wire OpenCV + OCR (Tesseract / Cloud Vision) later."""

    model_config = ConfigDict(populate_by_name=True)
    image_base64: Optional[str] = Field(None, alias="imageBase64")


class PipelineTextPayload(BaseModel):
    text: str = ""


class PipelineVoiceTranscribeRequest(BaseModel):
    """Audio blob base64 when you integrate Whisper — optional for now."""

    model_config = ConfigDict(populate_by_name=True)
    audio_base64: Optional[str] = Field(None, alias="audioBase64")
    note: Optional[str] = None


# ── App Setup ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (SQLite/Postgres). Use Alembic for managed migrations in production if needed."""
    db.init_db()
    _seed_admin_if_configured()
    yield


app = FastAPI(title="Voice2Sign", version="2.0.0", lifespan=lifespan)

_cors_origins = config.get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Device state (in-memory)
_device_state = {"mic": False, "camera": False}


# ── Auth Helper ──

def get_current_user(authorization: Optional[str] = Header(None)) -> dict | None:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    user_id = auth.decode_token(token)
    if not user_id:
        return None
    return db.get_user_by_id(user_id)


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    user = require_user(authorization)
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _seed_admin_if_configured() -> None:
    """Optional first admin from environment (not for public signup)."""
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    if db.get_user_by_email(email):
        return
    name = (os.getenv("ADMIN_NAME") or "Administrator").strip() or "Administrator"
    db.create_user(email, auth.hash_password(password), name, "admin")


# ── Health ──

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "voice2sign"}


# ── Auth Routes ──

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = db.get_user_by_email(req.email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "userType": user["user_type"],
        },
    }


@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    if req.userType not in ("hearing", "deaf"):
        raise HTTPException(status_code=400, detail="userType must be hearing or deaf")
    if db.get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    password_hash = auth.hash_password(req.password)
    name = f"{req.firstName} {req.lastName}".strip()
    user = db.create_user(req.email, password_hash, name, req.userType)
    token = auth.create_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "userType": user["user_type"],
        },
    }


@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    user = db.get_user_by_email(req.email)
    if user:
        reset_token = auth.create_token(user["id"])
        reset_link = f"http://localhost:5000/reset-password.html?token={reset_token}"
        
        print(f"\n--- PASSWORD RESET ---")
        print(f"Sending password reset link to: {req.email}")
        print(f"Reset Link: {reset_link}")
        print(f"----------------------\n")
        
        """
        # ==========================================
        # HOW TO IMPLEMENT EMAIL SENDING
        # ==========================================
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SMTP_USER = os.getenv("SMTP_USER", "your-email@gmail.com")
        SMTP_PASS = os.getenv("SMTP_PASS", "your-app-password") # Use an App Password!
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = req.email
        msg['Subject'] = "Voice2Sign - Password Reset"
        
        body = f"Hello {user['name']},\\n\\nClick the link below to reset your password:\\n{reset_link}\\n\\nIf you did not request this, please ignore this email."
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            print("Real Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
        """
        
    return {"message": "If this email exists, a reset link has been sent."}


@app.get("/api/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    """Current user profile (role drives dashboard layout)."""
    user = require_user(authorization)
    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "userType": user["user_type"],
        }
    }


@app.get("/api/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    """Aggregate counts — admin only; backed by SQLAlchemy / DATABASE_URL."""
    require_admin(authorization)
    return {
        "usersTotal": db.count_users(),
        "chatsTotal": db.count_chats(),
        "usersByType": {
            "hearing": db.count_users_by_type("hearing"),
            "deaf": db.count_users_by_type("deaf"),
            "admin": db.count_users_by_type("admin"),
        },
    }


# ── Chat Routes ──

@app.get("/api/chats")
def list_chats(authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    return {"chats": db.get_chats(user["id"])}


@app.post("/api/chats")
def create_chat(req: CreateChatRequest, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    chat = db.create_chat(user["id"], req.title)
    return {"chat": chat}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    if not db.delete_chat(chat_id, user["id"]):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"deleted": True}


@app.patch("/api/chats/{chat_id}/pin")
def pin_chat(chat_id: str, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    chat = db.toggle_pin_chat(chat_id, user["id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"chat": chat}


@app.get("/api/chats/{chat_id}/messages")
def list_messages(chat_id: str, authorization: Optional[str] = Header(None)):
    require_user(authorization)
    return {"messages": db.get_messages(chat_id)}


@app.post("/api/chats/{chat_id}/messages")
def send_message(chat_id: str, req: SendMessageRequest, authorization: Optional[str] = Header(None)):
    require_user(authorization)
    user_msg = db.add_message(chat_id, "user", req.content)

    # Generate a translation response
    response_text = generate_translation_response(req.content)
    assistant_msg = db.add_message(chat_id, "assistant", response_text)

    return {"userMessage": user_msg, "assistantMessage": assistant_msg}


def generate_translation_response(text: str) -> str:
    """Generate a simulated translation response."""
    text_lower = text.lower().strip()

    # Common greetings
    greetings = {
        "hello": "👋 Sign: Wave hand side to side. This is the universal greeting in ASL.",
        "hi": "👋 Sign: Open palm wave. A casual greeting in sign language.",
        "good morning": "🌅 Sign: Flat hand rises from chin (good) + arm rises like sunrise (morning).",
        "good night": "🌙 Sign: Flat hand from chin (good) + curved hand descends (night).",
        "thank you": "🙏 Sign: Touch fingertips to chin, then move hand forward. Express gratitude!",
        "thanks": "🙏 Sign: Fingertips from chin forward. A quick thank you gesture.",
        "please": "🤲 Sign: Open hand circles on chest clockwise.",
        "sorry": "😔 Sign: Fist circles on chest. Shows remorse or apology.",
        "yes": "✅ Sign: Fist nods up and down, like a nodding head.",
        "no": "❌ Sign: Index and middle finger snap to thumb.",
        "how are you": "💬 Sign: Point to person + curved hands move back and forth from body.",
        "i love you": "❤️ Sign: Extend thumb, index, and pinky finger. The iconic ILY sign!",
        "help": "🆘 Sign: Fist on flat palm, both rise together.",
        "my name is": "📛 Sign: Tap H-fingers together twice, then fingerspell your name.",
        "nice to meet you": "🤝 Sign: Both index fingers meet + point to person.",
        "goodbye": "👋 Sign: Open and close fingers repeatedly, like a wave goodbye.",
        "what": "❓ Sign: Shake relaxed hands with palms up.",
        "where": "📍 Sign: Wag index finger side to side.",
        "when": "⏰ Sign: Circle index finger around other index finger, then tap.",
        "why": "🤔 Sign: Touch forehead, pull away into Y-hand.",
        "who": "👤 Sign: Circle index finger around pursed lips.",
    }

    for key, response in greetings.items():
        if key in text_lower:
            return response

    # Default response for any text
    words = text.split()
    if len(words) <= 3:
        return f"✋ Translation: \"{text}\" → The sign involves specific hand shapes and movements. In ASL, short phrases are often expressed with clear, deliberate gestures."
    else:
        return f"✋ Translation: \"{text}\" → This phrase would be signed using a combination of {len(words)} signs in ASL. Each word maps to a specific gesture with defined hand shape, location, and movement."


# ── Preferences ──

@app.get("/api/preferences")
def get_preferences(authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    return {"preferences": db.get_preferences(user["id"])}


@app.put("/api/preferences")
def save_preferences(req: PreferencesRequest, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    saved = db.save_preferences(user["id"], req.data)
    return {"preferences": saved}


# ── Device Input Toggle ──

@app.post("/api/input/mic")
def toggle_mic(payload: InputToggleRequest):
    _device_state["mic"] = payload.active
    return {"device": "mic", "active": _device_state["mic"]}


@app.post("/api/input/camera")
def toggle_camera(payload: InputToggleRequest):
    _device_state["camera"] = payload.active
    return {"device": "camera", "active": _device_state["camera"]}


# ── ML / pipeline stubs (conceptual diagram flows — integrate OpenCV, Whisper, TTS, SD) ──

@app.get("/api/pipeline/status")
def pipeline_status():
    """Describes the two main flows for the dashboard UI."""
    return {
        "flows": {
            "sign_to_voice": {
                "steps": ["webcam", "image_recognition", "text", "text_to_voice", "sound"],
                "integrations": ["OpenCV", "Tesseract OCR / Google Cloud Vision", "pyttsx3", "Coqui TTS"],
                "limitation": "English hand signs only (per design)",
            },
            "voice_to_sign": {
                "steps": ["voice", "voice_to_text", "text", "text_to_image", "sign_image"],
                "integrations": ["OpenAI Whisper", "SpeechRecognition", "Stable Diffusion", "web API"],
            },
        }
    }


@app.post("/api/pipeline/sign-to-voice/recognize")
def pipeline_sign_to_voice_recognize(req: PipelineSignRecognizeRequest):
    """
    Stub: accept a JPEG base64 frame; return empty text until OpenCV + OCR is connected.
    """
    has_frame = bool(req.image_base64 and len(req.image_base64) > 50)
    return {
        "text": "",
        "stage": "image_recognition",
        "ready": False,
        "receivedFrame": has_frame,
        "integration": ["OpenCV", "Tesseract OCR", "Google Cloud Vision (optional)"],
        "message": "Stub: decode imageBase64, run pose/hand ROI + OCR, then return text.",
    }


@app.post("/api/pipeline/sign-to-voice/speak")
def pipeline_sign_to_voice_speak(req: PipelineTextPayload):
    """Stub: wire pyttsx3 or Coqui TTS and optionally return audio URL."""
    return {
        "text": req.text,
        "stage": "text_to_voice",
        "ready": False,
        "integration": ["pyttsx3", "Coqui TTS"],
        "message": "Stub: client may use browser speechSynthesis until server TTS is wired.",
    }


@app.post("/api/pipeline/voice-to-sign/transcribe")
def pipeline_voice_to_sign_transcribe(req: PipelineVoiceTranscribeRequest):
    """Stub: send audio to Whisper / SpeechRecognition when integrated."""
    return {
        "text": "",
        "stage": "voice_to_text",
        "ready": False,
        "integration": ["Whisper", "SpeechRecognition"],
        "message": "Stub: upload audio (multipart or base64) and return transcript.",
    }


@app.post("/api/pipeline/voice-to-sign/render")
def pipeline_voice_to_sign_render(req: PipelineTextPayload):
    """Stub: text → sign imagery via Stable Diffusion or a dedicated sign-avatar API."""
    return {
        "text": req.text,
        "imageUrl": None,
        "imageBase64": None,
        "stage": "text_to_image",
        "ready": False,
        "integration": ["Stable Diffusion", "web-based API"],
        "message": "Stub: generate or fetch sign illustration from text.",
    }


# ── Static Files & Root Redirect ──

@app.get("/")
def root():
    """Landing: translation dashboard (Sign→Voice / Voice→Sign). Auth is optional via header links."""
    return RedirectResponse(url="/dashboards/guest.html")


# Mount static files LAST so API routes take priority
STATIC_DIR = Path(__file__).resolve().parent.parent / "public"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
