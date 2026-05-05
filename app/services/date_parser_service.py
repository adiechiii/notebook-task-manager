from datetime import datetime, timedelta
import re


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_date_from_text(text: str):
    t = text.lower()
    today = datetime.utcnow().date()

    if re.search(r"\btoday\b", t):
        return today.isoformat()

    if re.search(r"\btomorrow\b", t):
        return (today + timedelta(days=1)).isoformat()

    for day, idx in WEEKDAYS.items():
        if re.search(rf"\b{day}\b", t):
            current_weekday = today.weekday()
            delta = (idx - current_weekday) % 7
            delta = 7 if delta == 0 else delta
            return (today + timedelta(days=delta)).isoformat()

    return ""


def normalize_task_title(text: str):
    title = text.strip()

    date_pattern = (
        r"\b(?:on|by|for)?\s*"
        r"(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    )

    title = re.sub(date_pattern, "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip()
    title = title.strip(" -.,;:")

    return title if title else text.strip()
