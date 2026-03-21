from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class InputToggleRequest(BaseModel):
    active: bool


app = FastAPI(title="Voice2Sign Input Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = {"mic": False, "camera": False}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "voice2sign-backend"}


@app.post("/api/input/mic")
def toggle_mic(payload: InputToggleRequest) -> dict:
    state["mic"] = payload.active
    return {"device": "mic", "active": state["mic"]}


@app.post("/api/input/camera")
def toggle_camera(payload: InputToggleRequest) -> dict:
    state["camera"] = payload.active
    return {"device": "camera", "active": state["camera"]}

