from googleapiclient.discovery import build
from tools.google_client import get_google_credentials
from core.agent import OllamaClient
from datetime import datetime, timezone, timedelta
import json
import re

GOOGLE_SYSTEM = """
You are a helpful assistant. You will be given raw data from Google APIs.
Summarize it conversationally in 1-3 sentences.
"""

INTENT_SYSTEM = """
You are an intent classifier for Google account actions.
Classify the query into one of: read_email, read_calendar, add_reminder.

Rules:
- Emails, inbox, unread messages → read_email
- Calendar, events, meetings, schedule → read_calendar  
- Remind, add, create, set, schedule a reminder or appointment → add_reminder

For add_reminder output:
{{
  "intent": "add_reminder",
  "title": "<what the reminder is for>",
  "date": "<YYYY-MM-DD or null>",
  "time": "<HH:MM 24hr or null>",
  "duration_minutes": 30,
  "description": null
}}

For others output:
{{"intent": "read_email"}} or {{"intent": "read_calendar"}}

Today: {today}
Time: {now}
"""

class GoogleAgent:
    def __init__(self, llm: OllamaClient = None):
        self.llm = llm or OllamaClient()
        creds = get_google_credentials()
        self.calendar = build("calendar", "v3", credentials=creds)
        self.gmail    = build("gmail", "v1", credentials=creds)

    def _classify(self, query: str) -> dict:
        now = datetime.now()
        system = INTENT_SYSTEM.format(
            today=now.strftime("%Y-%m-%d"),
            now=now.strftime("%H:%M"),
        )
        # Use structured_output which forces JSON at the model level
        parsed = self.llm.structured_output(query, system=system)
        print(f"[GoogleAgent] Parsed: {parsed}")
        return parsed

    def get_upcoming_events(self, max_results: int = 5) -> str:
        now = datetime.now(timezone.utc).isoformat()
        events_result = self.calendar.events().list(
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
        return self.llm.generate(
            f"Summarize these calendar events:\n{raw}",
            system=GOOGLE_SYSTEM
        )

    def get_unread_emails(self, max_results: int = 5) -> str:
        result = self.gmail.users().messages().list(
            userId="me", labelIds=["UNREAD"], maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        if not messages:
            return "No unread emails."

        summaries = []
        for msg in messages:
            m = self.gmail.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            summaries.append(f"From: {headers.get('From')} | Subject: {headers.get('Subject')}")

        raw = "\n".join(summaries)
        return self.llm.generate(
            f"Summarize these unread emails:\n{raw}",
            system=GOOGLE_SYSTEM
        )

    def add_reminder(self, parsed: dict) -> str:
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

        created = self.calendar.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()

        title    = created.get("summary")
        start    = created.get("start", {}).get("dateTime", "")
        link     = created.get("htmlLink", "")
        readable = datetime.fromisoformat(start).strftime("%B %d at %I:%M %p")

        return f"Done! Reminder set for '{title}' on {readable}. You'll get a popup 10 min before and an email 30 min before.\nCalendar link: {link}"

    def run(self, query: str) -> str:
        print(f"[GoogleAgent] Query received: {query}")
        try:
            parsed = self._classify(query)
        except Exception as e:
            print(f"[GoogleAgent] Classification failed: {e}. Falling back to keyword match.")
            q = query.lower()
            if any(w in q for w in ["email", "mail", "inbox", "unread"]):
                return self.get_unread_emails()
            if any(w in q for w in ["remind", "add", "create", "set", "schedule", "appointment"]):
                return "I understood you want to add a reminder, but couldn't parse the details. Try: 'Remind me to call John tomorrow at 3pm'"
            if any(w in q for w in ["calendar", "event", "meeting"]):
                return self.get_upcoming_events()
            return "I can check your email, calendar, or add a reminder. What do you need?"

        intent = parsed.get("intent", "").strip().lower()
        print(f"[GoogleAgent] Intent resolved: '{intent}'")

        if intent == "add_reminder":
            return self.add_reminder(parsed)
        elif intent == "read_email":
            return self.get_unread_emails()
        elif intent == "read_calendar":
            return self.get_upcoming_events()
        else:
            print(f"[GoogleAgent] Unknown intent '{intent}' — falling back to keyword match.")
            q = query.lower()
            if any(w in q for w in ["email", "mail", "inbox"]):
                return self.get_unread_emails()
            if any(w in q for w in ["remind", "add", "create", "set"]):
                return "Couldn't parse reminder details. Try: 'Remind me to call John tomorrow at 3pm'"
            return self.get_upcoming_events()