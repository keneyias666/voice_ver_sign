# Voice2Sign

A voice-to-sign language translation web application with a clean HTML/CSS/JS frontend and a Python FastAPI backend.

## Project Structure

```
voice_to_sign/
├── index.html          # Login page (landing)
├── signup.html         # Signup page
├── dashboard.html      # Main dashboard
├── serve.py            # Python HTTP server for frontend (port 5000)
├── css/
│   ├── main.css        # Core styles, variables, utilities
│   ├── login.css       # Login page specific styles
│   ├── signup.css      # Signup page specific styles
│   └── dashboard.css   # Dashboard specific styles
├── js/
│   ├── main.js         # Theme management, utilities, toast
│   ├── auth.js         # Authentication (login/signup)
│   └── dashboard.js    # Dashboard functionality
├── images/             # Logo and image assets
├── assets/             # Additional static assets
├── backend/
│   ├── app.py          # FastAPI application
│   └── requirements.txt
└── reference/          # Reference materials
```

## Architecture

- **Frontend**: Static HTML/CSS/JS served by Python's built-in HTTP server on port 5000
- **Backend**: FastAPI server on port 8000 (localhost only)
- **Languages**: Python 3.12, HTML/CSS/JavaScript

## Workflows

- **Start application**: `python serve.py` — serves the static frontend on `0.0.0.0:5000`
- **Backend API**: `uvicorn backend.app:app --host localhost --port 8000` — runs the FastAPI backend

## Backend API Endpoints

- `GET /api/health` — Health check
- `POST /api/input/mic` — Toggle microphone state `{ "active": bool }`
- `POST /api/input/camera` — Toggle camera state `{ "active": bool }`

## Design System

- **Colors**: White/black backgrounds, skin-tone accent (#D4A574)
- **Font**: Work Sans (Google Fonts)
- **Themes**: Light/dark mode with smooth transitions

## Deployment

Configured for autoscale deployment. Both services start via:
```bash
uvicorn backend.app:app --host localhost --port 8000 & python serve.py
```
