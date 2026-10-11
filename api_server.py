import os
import sys
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(override=True)

from calendar_tool import check_availability, book_meeting, get_calendar_service

app = Flask(__name__)
# Enable CORS for all routes (allows calls from http://localhost:8000 and any other frontend origin)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/ui", methods=["GET"])
def serve_ui():
    """
    Serve the interactive NovaVoice frontend directly from the Flask server.
    """
    return send_file("index.html")

def check_calendar_integration():
    """
    Checks if Google Calendar integration is authenticated and operational.
    Returns (is_connected: bool, message: str).
    """
    try:
        get_calendar_service()
        return True, "Google Calendar API connection active"
    except FileNotFoundError:
        return False, "token.json not found. Run auth_server.py first to authorize Google Calendar."
    except Exception as e:
        return False, f"Calendar authentication error: {str(e)}"

@app.route("/", methods=["GET"])
def root():
    """
    Root endpoint returning server status, application name, and available endpoints.
    """
    cal_ok, cal_msg = check_calendar_integration()
    return jsonify({
        "app": "NovaVoice Calendar Bridge",
        "status": "running",
        "message": "NovaVoice Calendar Bridge API is operational.",
        "calendar_connected": cal_ok,
        "endpoints": {
            "root": "GET /",
            "health": "GET /health",
            "api_health": "GET /api/health",
            "check_availability": "POST /api/check_availability",
            "book_meeting": "POST /api/book_meeting"
        }
    }), 200

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint reporting bridge status and calendar integration status.
    Returns HTTP 200 if healthy, HTTP 503 if calendar integration is unavailable.
    """
    cal_ok, cal_msg = check_calendar_integration()
    status_code = 200 if cal_ok else 503
    return jsonify({
        "service": "NovaVoice Calendar Bridge",
        "status": "healthy" if cal_ok else "degraded",
        "calendar_integration": {
            "connected": cal_ok,
            "message": cal_msg
        }
    }), status_code

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    """
    Handle browser favicon requests gracefully to avoid 404 noise.
    """
    return ("", 204)

@app.route("/api/check_availability", methods=["POST"])
def handle_check_availability():
    data = request.get_json(silent=True) or {}
    date_val = data.get("date") or data.get("date_iso")
    
    print(f"📅 checking availability for: {date_val}")
    
    if not date_val:
        err = "Error: 'date' parameter is required."
        print(f"❌ {err}")
        return jsonify({"result": err}), 400
        
    result = check_availability(date_val)
    print(f"✅ response:\n{result}\n")
    return jsonify({"result": result}), 200

@app.route("/api/book_meeting", methods=["POST"])
def handle_book_meeting():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "NovaVoice Demo")
    date_time = data.get("date_time") or data.get("dateTime")
    guest_email = data.get("guest_email") or data.get("name") or data.get("guest") or "Guest"
    
    print(f"🔔 booking meeting: '{title}' at {date_time} for {guest_email}")
    
    if not date_time:
        err = "Error: 'date_time' parameter is required."
        print(f"❌ {err}")
        return jsonify({"result": err}), 400
        
    result = book_meeting(date_time, guest_email)
    print(f"✅ response: {result}\n")
    return jsonify({"result": result}), 200

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on this server.",
        "status": 404
    }), 404

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({
        "error": "Method Not Allowed",
        "message": "The method is not allowed for the requested URL.",
        "status": 405
    }), 405

@app.errorhandler(500)
def handle_internal_error(e):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred on the server.",
        "status": 500
    }), 500

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 NovaVoice Calendar Bridge API Server starting on http://127.0.0.1:5000")
    print("Listening for tool calls from frontend...")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
