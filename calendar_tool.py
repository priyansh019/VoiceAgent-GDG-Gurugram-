import os
import sys
import re
from datetime import datetime, date, time, timedelta, timezone
from dotenv import load_dotenv

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(override=True)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

def get_calendar_service():
    """
    Loads OAuth credentials from token.json and returns an authorized Google Calendar v3 service.
    Raises FileNotFoundError if token.json is missing.
    """
    token_path = "token.json"
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            "token.json not found! Please run auth_server.py first to authorize Google Calendar and generate token.json."
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
        except Exception as refresh_err:
            print(f"❌ Failed to refresh expired credentials: {refresh_err}")
            raise

    return build("calendar", "v3", credentials=creds)

def parse_iso_datetime(date_str):
    """
    Parses an ISO 8601 date or datetime string, tolerating trailing Z and timezone offsets.
    Returns (dt_object, tzinfo).
    """
    cleaned = date_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    # Match simple date format YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        local_tz = datetime.now().astimezone().tzinfo
        d = date.fromisoformat(cleaned)
        dt = datetime.combine(d, time.min, tzinfo=local_tz)
        return dt, local_tz

    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz)
        return dt, dt.tzinfo
    except Exception as err:
        raise ValueError(f"Could not parse ISO date/datetime '{date_str}': {err}")

def check_availability(date_iso):
    """
    Checks calendar availability for the day specified in date_iso.
    Lists events from 00:00 to 23:59:59 on that day on HOST_CALENDAR_ID.
    Returns:
      "The calendar is completely free on YYYY-MM-DD." or a list of "Blocked from START to END (SUMMARY)" lines.
    """
    try:
        host_calendar_id = os.getenv("HOST_CALENDAR_ID", "primary") or "primary"
        dt, tz = parse_iso_datetime(date_iso)
        
        target_date_str = dt.strftime("%Y-%m-%d")
        start_of_day = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=tz)
        end_of_day = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=tz)

        service = get_calendar_service()
        events_result = service.events().list(
            calendarId=host_calendar_id,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"The calendar is completely free on {target_date_str}."

        blocked_lines = []
        for event in events:
            summary = event.get("summary", "Busy / Untitled Event")
            start_raw = event.get("start", {})
            end_raw = event.get("end", {})

            if "dateTime" in start_raw:
                s_dt, _ = parse_iso_datetime(start_raw["dateTime"])
                start_formatted = s_dt.strftime("%H:%M")
            else:
                start_formatted = "All Day"

            if "dateTime" in end_raw:
                e_dt, _ = parse_iso_datetime(end_raw["dateTime"])
                end_formatted = e_dt.strftime("%H:%M")
            else:
                end_formatted = "All Day"

            blocked_lines.append(f"Blocked from {start_formatted} to {end_formatted} ({summary})")

        return "\n".join(blocked_lines)

    except Exception as e:
        error_msg = f"Failed to check calendar availability: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg

def book_meeting(date_time_iso, name):
    """
    Books a 30-minute meeting on Google Calendar for the given name.
    Event summary: "NovaVoice Demo: {name}"
    Description: "Automated booking created via Gemini Live AI Calling Assistant."
    Prints the event's htmlLink and returns success message.
    """
    try:
        host_calendar_id = os.getenv("HOST_CALENDAR_ID", "primary") or "primary"
        start_dt, tz = parse_iso_datetime(date_time_iso)
        end_dt = start_dt + timedelta(minutes=30)

        event_body = {
            "summary": f"NovaVoice Demo: {name}",
            "description": "Automated booking created via Gemini Live AI Calling Assistant.",
            "start": {
                "dateTime": start_dt.isoformat(),
            },
            "end": {
                "dateTime": end_dt.isoformat(),
            },
        }

        service = get_calendar_service()
        created_event = service.events().insert(
            calendarId=host_calendar_id,
            body=event_body
        ).execute()

        html_link = created_event.get("htmlLink", "(link unavailable)")
        print(f"📅 Event booked successfully! Link: {html_link}")

        return f"Success! Meeting booked on Google Calendar for {name}."

    except Exception as e:
        error_msg = f"Failed to book meeting: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
