# 🎙️ NovaVoice - Real-Time Voice AI Booking Assistant

NovaVoice is a real-time, speech-to-speech AI calling assistant that connects callers with Google Calendar. Powered directly by the **Gemini Live API (`BidiGenerateContent`)** and a lightweight Python bridge for tool execution, NovaVoice allows natural, interruptible voice conversations to check availability and book meetings.

---

## 🏛️ Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Browser (http://localhost:8000)          │
│                                                        │
│  - Captures 16 kHz PCM audio from mic                  │
│  - Streams bidirectional audio to Gemini Live API      │
│  - Plays 24 kHz PCM audio with barge-in support       │
│  - Real-time animated volume visualizer                │
└──────────────▲──────────────────────────▲──────────────┘
               │                          │
 (WebSocket Direct wss://...)     (HTTP POST tool calls)
               │                          │
               ▼                          ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│      Gemini Live API      │   │   Python Calendar Bridge  │
│  (models/gemini-3.1-flash │   │      (api_server.py)      │
│      -live-preview)       │   │   http://127.0.0.1:5000   │
└───────────────────────────┘   └─────────────┬─────────────┘
                                              │ (OAuth v3)
                                              ▼
                                ┌───────────────────────────┐
                                │      Google Calendar      │
                                └───────────────────────────┘
```

1. **Direct Frontend WebSocket**: The browser connects directly to `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=YOUR_API_KEY`.
2. **Local Bridge for Tools**: When Gemini issues a `toolCall` (`check_availability` or `book_meeting`), the browser POSTs the arguments to the local Python bridge running on port 5000 (`api_server.py`), which uses credentials from `token.json` to talk to Google Calendar.
3. **Security**: Google OAuth credentials and `token.json` never reach the browser or client bundle.

---

## 📂 Project Structure

- `index.html`: Single-file modern dark frontend (pure HTML5 / CSS3 / Vanilla JS).
- `auth_server.py`: One-time Flask OAuth server on port 8000 to authenticate with Google Calendar and generate `token.json`.
- `calendar_tool.py`: Core Calendar v3 integration (`check_availability` and `book_meeting`).
- `api_server.py`: Flask + CORS bridge on port 5000 exposing calendar endpoints to the frontend.
- `requirements.txt`: Python package dependencies.
- `.env.example`: Template for environment variables.
- `.gitignore`: Configured to ignore secrets, virtual environments, and tokens.

---

## ⚙️ Prerequisites & Setup

### 1. Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Or on Windows (Command Prompt):
.\venv\Scripts\activate.bat
# Or on macOS/Linux:
source venv/bin/activate
```

> **Note on macOS**: If installing `PyAudio` from source, install PortAudio first: `brew install portaudio`.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Google Cloud OAuth 2.0 Setup

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable the **Google Calendar API**:
   - Go to **APIs & Services > Library**.
   - Search for **Google Calendar API** and click **Enable**.
4. Configure the **OAuth Consent Screen**:
   - Go to **APIs & Services > OAuth consent screen**.
   - Select **External** and click **Create**.
   - Fill in app name (e.g., `NovaVoice`), support email, and developer contact email.
   - Under **Scopes**, click **Add or Remove Scopes** and add:
     - `https://www.googleapis.com/auth/calendar.events`
   - Under **Test Users**, add your Gmail address (the one hosting the calendar).
   - Save and continue.
5. Create **OAuth 2.0 Client ID**:
   - Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `NovaVoice Web Client`.
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/callback`
   - Click **Create**. Copy the **Client ID** and **Client Secret**.

---

## 📄 Environment Configuration (.env)

Create a `.env` file in the project root (you can copy `.env.example`):

```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
HOST_CALENDAR_ID=your-email@gmail.com
HOST_EMAIL=your-email@gmail.com
FRONTEND_URL=http://localhost:8000
SECRET_KEY=generate-a-secure-random-secret-key-here
```

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID from Google Cloud Console. |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret from Google Cloud Console. |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/auth/callback` |
| `HOST_CALENDAR_ID` | Host's calendar ID (usually your Gmail address, or `primary`). |
| `HOST_EMAIL` | Host email address for meeting notifications. |
| `FRONTEND_URL` | Frontend origin (`http://localhost:8000`). |
| `SECRET_KEY` | Flask session secret key. |

---

## 🚀 Running NovaVoice

### Step 1: Run OAuth Authorization (One-time)

Run the one-time authentication server on port 8000:

```bash
python auth_server.py
```

1. Open your browser at [http://localhost:8000](http://localhost:8000).
2. Click **"Click here to Authorize Google Calendar"**.
3. Sign in with your host Google account and grant calendar permissions.
4. When you see the green **"Authorization Successful!"** page, `token.json` has been created.
5. **Stop the auth server** in your terminal by pressing `Ctrl + C`.

---

### Step 2: Start the Python Bridge API (Terminal 1)

In your first terminal, start the local bridge on port 5000:

```bash
python api_server.py
```

You should see:
```
============================================================
🚀 NovaVoice Calendar Bridge API Server starting on http://127.0.0.1:5000
Listening for tool calls from frontend...
============================================================
```

---

### Step 3: Serve the Frontend (Terminal 2)

In a second terminal, serve `index.html` on port 8000:

```bash
python -m http.server 8000
```

---

### Step 4: Open and Talk to NovaVoice

1. Open [http://localhost:8000](http://localhost:8000) in Chrome, Edge, or Firefox.
2. In the setup modal, paste your **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/)).
3. Click **Connect to Agent**.
4. Allow microphone access when prompted.
5. Click the large round 🎙️ microphone button:
   - The ring will pulse as NovaVoice speaks with the **Charon** voice.
   - Speak naturally to check your schedule: *"Can you check my availability for tomorrow afternoon?"*
   - NovaVoice will trigger `check_availability()` and show a dashed green tool card in the transcript.
   - Say: *"Book a meeting for Sarah at 2:00 PM tomorrow."*
   - NovaVoice will invoke `book_meeting()`, create the Google Calendar event, and confirm the details with you.
6. Interruption (Barge-in): You can speak at any time while the agent is talking; playback stops immediately and the agent listens to you.
7. Click the button again (⏹️) to end the call anytime.


## Not a full Project
