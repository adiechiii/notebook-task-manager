from datetime import datetime, timedelta

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}


def parse_date_from_text(text: str):
    t = text.lower()
    today = datetime.utcnow().date()

    # today
    if "today" in t:
        return today.isoformat()

    # tomorrow
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat()

    # weekdays
    for day, idx in WEEKDAYS.items():
        if day in t:
            current_weekday = today.weekday()
            delta = (idx - current_weekday) % 7
            delta = 7 if delta == 0 else delta
            return (today + timedelta(days=delta)).isoformat()

    return ""