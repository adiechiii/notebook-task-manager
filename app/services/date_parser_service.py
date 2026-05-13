from datetime import date, datetime, timedelta
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


MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


LEADING_SCHEDULE_WORDS = r"(?:due(?:\s+on)?|on|by|for)"
WEEKDAY_PATTERN = "|".join(WEEKDAYS)
MONTH_PATTERN = "|".join(MONTHS)


def _today():
    return datetime.utcnow().date()


def _last_day_of_month(year, month):
    if month == 12:
        first_next_month = date(year + 1, 1, 1)
    else:
        first_next_month = date(year, month + 1, 1)

    return first_next_month - timedelta(days=1)


def _next_month(year, month):
    if month == 12:
        return year + 1, 1

    return year, month + 1


def _weekday_date(today, weekday_idx, modifier=None):
    current_weekday = today.weekday()

    if modifier == "next":
        days_until = (weekday_idx - current_weekday) % 7
        return today + timedelta(days=days_until + 7)

    delta = (weekday_idx - current_weekday) % 7

    if modifier == "this":
        return today + timedelta(days=delta)

    delta = 7 if delta == 0 else delta
    return today + timedelta(days=delta)


def _month_day_date(today, month_name, day_text):
    month = MONTHS[month_name.lower()]
    day = int(day_text)

    try:
        parsed_date = date(today.year, month, day)
    except ValueError:
        return None

    if parsed_date < today:
        try:
            parsed_date = date(today.year + 1, month, day)
        except ValueError:
            return None

    return parsed_date


def _build_match(match, parsed_date):
    if not parsed_date:
        return None

    return {
        "date": parsed_date.isoformat(),
        "start": match.start(),
        "end": match.end(),
    }


def _search(text, pattern):
    return re.search(
        rf"\b(?:{LEADING_SCHEDULE_WORDS}\s+)?{pattern}\b",
        text,
        flags=re.IGNORECASE,
    )


def _matched_date_phrase(text: str):
    today = _today()

    match = _search(text, r"\d{4}-\d{2}-\d{2}")
    if match:
        date_text = re.search(r"\d{4}-\d{2}-\d{2}", match.group(0)).group(0)
        try:
            return _build_match(match, date.fromisoformat(date_text))
        except ValueError:
            return None

    match = _search(text, r"tomorrow\s+(?:morning|afternoon|evening)")
    if match:
        return _build_match(match, today + timedelta(days=1))

    match = _search(text, r"tomorrow")
    if match:
        return _build_match(match, today + timedelta(days=1))

    match = _search(text, r"(?:today|tonight)")
    if match:
        return _build_match(match, today)

    match = _search(text, r"end\s+of\s+next\s+month")
    if match:
        year, month = _next_month(today.year, today.month)
        return _build_match(match, _last_day_of_month(year, month))

    match = _search(text, r"end\s+of\s+month")
    if match:
        return _build_match(match, _last_day_of_month(today.year, today.month))

    match = _search(text, r"next\s+week")
    if match:
        return _build_match(match, today + timedelta(days=7))

    match = _search(text, r"in\s+\d+\s+days?")
    if match:
        amount = int(re.search(r"\d+", match.group(0)).group(0))
        return _build_match(match, today + timedelta(days=amount))

    match = _search(text, r"in\s+\d+\s+weeks?")
    if match:
        amount = int(re.search(r"\d+", match.group(0)).group(0))
        return _build_match(match, today + timedelta(days=amount * 7))

    match = _search(text, rf"(?:{MONTH_PATTERN})\s+\d{{1,2}}")
    if match:
        month_day_match = re.search(
            rf"\b({MONTH_PATTERN})\s+(\d{{1,2}})\b",
            match.group(0),
            flags=re.IGNORECASE,
        )
        parsed_date = _month_day_date(
            today,
            month_day_match.group(1),
            month_day_match.group(2),
        )
        return _build_match(match, parsed_date)

    match = _search(text, rf"(?:this|next)\s+(?:{WEEKDAY_PATTERN})")
    if match:
        weekday_match = re.search(
            rf"\b(this|next)\s+({WEEKDAY_PATTERN})\b",
            match.group(0),
            flags=re.IGNORECASE,
        )
        modifier = weekday_match.group(1).lower()
        weekday = weekday_match.group(2).lower()
        return _build_match(
            match,
            _weekday_date(today, WEEKDAYS[weekday], modifier=modifier),
        )

    match = _search(text, rf"(?:{WEEKDAY_PATTERN})")
    if match:
        weekday_match = re.search(
            rf"\b({WEEKDAY_PATTERN})\b",
            match.group(0),
            flags=re.IGNORECASE,
        )
        weekday = weekday_match.group(1).lower()
        return _build_match(match, _weekday_date(today, WEEKDAYS[weekday]))

    return None


def parse_date_from_text(text: str):
    match = _matched_date_phrase(text)
    return match["date"] if match else ""


def normalize_task_title(text: str):
    title = text.strip()
    match = _matched_date_phrase(title)

    if match:
        title = f"{title[:match['start']]} {title[match['end']:]}"

    title = re.sub(r"\s+", " ", title).strip()
    title = title.strip(" -.,;:")
    title = re.sub(r"\b(?:due|by|on|for)$", "", title, flags=re.IGNORECASE).strip()
    title = title.strip(" -.,;:")

    return title if title else text.strip()
