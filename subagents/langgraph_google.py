from langchain_core.agents import tool
from datetime import datetime, timezone, timedelta
from tools.google_client import get_google_credentials
from googleapiclient.discovery import build



GOOGLE_SYSTEM = """
You are a helpful assistant. You will be given raw data from Google APIs.
Summarize it conversationally in 1-3 sentences.
"""

calendar = build("calendar", "v3", credentials=get_google_credentials())
gmail = build("gmail", "v1", credentials=get_google_credentials())


@tool
def get_upcoming_events(max_results: int = 5) -> str:
    now = datetime.now(timezone.utc).isoformat()
    events_result = calendar.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = events_result.get("items", [])
    if not events:
        return "No upcoming events found."
    raw = "\n".join(
        f"- {e['summary']} at {e['start'].get('dateTime', e['start'].get('date'))}"
        for e in events
    )
    return raw


@tool
def get_unread_emails(max_results: int = 5) -> str:
    result = gmail.users().messages().list(
        userId="me", labelIds=["UNREAD"], maxResults=max_results
    ).execute()
    messages = result.get("messages", [])
    if not messages:
        return "No unread emails."

    summaries = []
    for msg in messages:
        m = gmail.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject"]
        ).execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        summaries.append(f"From: {headers.get('From')} | Subject: {headers.get('Subject')}")

    raw = "\n".join(summaries)
    return raw


@tool
def add_reminder(parsed: dict) -> str:
    now = datetime.now()

    # --- Resolve date ---
    if parsed.get("date"):
        event_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
    else:
        event_date = now.date()  # default to today

    # --- Resolve time ---
    if parsed.get("time"):
        event_time = datetime.strptime(parsed["time"], "%H:%M").time()
    else:
        # Default: 1 hour from now, rounded to next half hour
        next_hour = now + timedelta(hours=1)
        minutes = 0 if next_hour.minute < 30 else 30
        event_time = next_hour.replace(minute=minutes, second=0, microsecond=0).time()

    duration = parsed.get("duration_minutes", 30)

    start_dt = datetime.combine(event_date, event_time)
    end_dt   = start_dt + timedelta(minutes=duration)

    # Format as RFC3339 with local timezone offset
    tz_offset = datetime.now(timezone.utc).astimezone().strftime("%z")
    tz_str    = f"{tz_offset[:3]}:{tz_offset[3:]}"  # e.g. "-05:00"

    start_str = start_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")
    end_str   = end_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")

    event_body = {
        "summary": parsed.get("title", "Reminder"),
        "description": parsed.get("description") or "",
        "start": {"dateTime": start_str},
        "end":   {"dateTime": end_str},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup",  "minutes": 10},
                {"method": "email",  "minutes": 30},
            ],
        },
    }

    created = calendar.events().insert(
        calendarId="primary",
        body=event_body
    ).execute()

    title    = created.get("summary")
    start    = created.get("start", {}).get("dateTime", "")
    link     = created.get("htmlLink", "")
    readable = datetime.fromisoformat(start).strftime("%B %d at %I:%M %p")

    return f"Done! Reminder set for '{title}' on {readable}. You'll get a popup 10 min before and an email 30 min before.\nCalendar link: {link}"
