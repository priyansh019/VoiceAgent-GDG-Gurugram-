import os
import sys
from flask import Flask, redirect, request, render_template_string
from dotenv import load_dotenv

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google_auth_oauthlib.flow import Flow

# Load environment variables (force override to ensure file changes take effect)
load_dotenv(override=True)

# Allow insecure transport for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "novavoice-insecure-secret-key-for-auth")

# Calendar Events Scope
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

def get_client_config():
    client_id = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
    
    if not client_id or not client_secret or "your-google-client-id" in client_id:
        return None
        
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

def create_flow(state=None):
    client_config = get_client_config()
    if not client_config:
        raise ValueError(
            "Missing or unconfigured GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env file. "
            "Please check your .env file."
        )
    redirect_uri = (os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback") or "").strip()
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=state
    )

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NovaVoice - Google Calendar Authorization</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 1rem;
            padding: 2.5rem;
            max-width: 480px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
        }
        h1 {
            margin-top: 0;
            font-size: 1.75rem;
            color: #f8fafc;
        }
        p {
            color: #94a3b8;
            line-height: 1.5;
            margin-bottom: 2rem;
        }
        .btn {
            display: inline-block;
            background-color: #3b82f6;
            color: #ffffff;
            text-decoration: none;
            padding: 0.85rem 1.75rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.2s ease;
        }
        .btn:hover {
            background-color: #2563eb;
            transform: translateY(-1px);
        }
        .alert {
            background-color: #451a1a;
            border: 1px solid #7f1d1d;
            color: #fca5a5;
            padding: 1rem;
            border-radius: 0.5rem;
            text-align: left;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>AI Calling Assistant</h1>
        {% if error %}
            <div class="alert">
                <strong>Configuration Error:</strong><br>{{ error }}
            </div>
        {% else %}
            <p>Authorize NovaVoice to connect with your Google Calendar to manage availability and automatically schedule meetings.</p>
            <a class="btn" href="{{ auth_url }}">Click here to Authorize Google Calendar</a>
        {% endif %}
    </div>
</body>
</html>
"""

CALLBACK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authorization Successful - NovaVoice</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background-color: #1e293b;
            border: 1px solid #10b981;
            border-radius: 1rem;
            padding: 2.5rem;
            max-width: 480px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
        }
        .badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 4rem;
            height: 4rem;
            background-color: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border-radius: 50%;
            font-size: 2rem;
            margin-bottom: 1.25rem;
        }
        h1 {
            margin-top: 0;
            font-size: 1.75rem;
            color: #f8fafc;
        }
        p {
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .instruction {
            background-color: #0f172a;
            border: 1px dashed #334155;
            padding: 1rem;
            border-radius: 0.5rem;
            font-family: monospace;
            color: #38bdf8;
            font-size: 0.95rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">✓</div>
        <h1>Authorization Successful!</h1>
        <p>Google Calendar credentials have been saved to <strong>token.json</strong>.</p>
        <div class="instruction">
            You can now stop this server (press Ctrl+C in terminal) and start the main NovaVoice services.
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    try:
        from flask import session
        flow = create_flow()
        authorization_url, state = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true"
        )
        # Store state and PKCE code_verifier in session
        session["state"] = state
        session["code_verifier"] = getattr(flow, "code_verifier", None)
        return render_template_string(INDEX_HTML, auth_url=authorization_url)
    except Exception as e:
        return render_template_string(INDEX_HTML, error=str(e))

@app.route("/auth/callback")
def auth_callback():
    try:
        from flask import session
        state = session.get("state")
        code_verifier = session.get("code_verifier")
        
        flow = create_flow(state=state)
        if code_verifier:
            flow.code_verifier = code_verifier

        # Fetch token with authorization response URL
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Save credentials to token.json
        with open("token.json", "w", encoding="utf-8") as token_file:
            token_file.write(credentials.to_json())
            
        print("\n✅ Successfully received OAuth credentials and saved to token.json!")
        print("🛑 You can now stop this auth server (Ctrl+C).\n")
        return render_template_string(CALLBACK_HTML)
    except Exception as e:
        return f"<div style='background:#0f172a;color:#fca5a5;padding:2rem;font-family:sans-serif;'><h3>❌ Authorization Error:</h3><p>{str(e)}</p></div>", 500

if __name__ == "__main__":
    print("🚀 Starting NovaVoice OAuth setup server on http://localhost:8000 ...")
    print("👉 Open http://localhost:8000 in your browser to authorize Google Calendar.")
    app.run(host="localhost", port=8000, debug=False)
