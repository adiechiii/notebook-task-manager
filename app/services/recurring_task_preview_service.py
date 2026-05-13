from datetime import date, datetime, timedelta
import re

from app.services.category_service import classify_category
from app.services.priority_service import parse_priority_from_text


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

HORIZON_MIN_DAYS = 1
HORIZON_MAX_DAYS = 366
DEFAULT_HORIZON_DAYS = 90
DEFAULT_TIMEZONE = "Etc/UTC"


def _today():
    return datetime.utcnow().date()


def _parse_anchor_date(value):
    if not value:
        return _today(), None

    try:
        return date.fromisoformat(str(value).strip()), None
    except ValueError:
        return _today(), "Invalid anchor_date; defaulted to today."


def _clamp_horizon_days(value):
    if value is None:
        return DEFAULT_HORIZON_DAYS, None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_HORIZON_DAYS, "Invalid horizon_days; defaulted to 90."

    clamped = min(max(parsed, HORIZON_MIN_DAYS), HORIZON_MAX_DAYS)
    if clamped != parsed:
        return clamped, "horizon_days was clamped to the supported range 1-366."

    return clamped, None


def _ordinal_day(value):
    match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", str(value or "").strip(), re.IGNORECASE)
    if not match:
        return None

    day = int(match.group(1))
    if 1 <= day <= 31:
        return day

    return None


def _last_day_of_month(year, month):
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)

    return date(year, month + 1, 1) - timedelta(days=1)


def _safe_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return _last_day_of_month(year, month)


def _next_month(year, month):
    if month == 12:
        return year + 1, 1

    return year, month + 1


def _month_names_pattern():
    return "|".join(sorted(MONTHS, key=len, reverse=True))


def _weekday_names_pattern():
    return "|".join(WEEKDAYS)


def _extract_weekdays(text):
    names = re.findall(rf"\b({_weekday_names_pattern()})\b", text, flags=re.IGNORECASE)
    days = []
    seen = set()

    for name in names:
        key = name.lower()
        if key in seen:
            continue

        seen.add(key)
        days.append(key)

    return days


def _has_unsupported_pattern(text):
    unsupported = [
        (r"\blast\s+business\s+day\b", "Unsupported recurrence pattern: last business day."),
        (r"\bskip\s+weekends?\b", "Unsupported recurrence pattern: skip weekends."),
        (
            rf"\bevery\s+\d+(?:st|nd|rd|th)?\s+(?:{_weekday_names_pattern()})\b",
            "Unsupported recurrence pattern: ordinal weekdays.",
        ),
        (r"\bbusiness\s+days?\b", "Unsupported recurrence pattern: business days."),
        (r"\brrule\b", "Unsupported recurrence pattern: RRULE-style rules."),
    ]

    warnings = []
    matched_last_business_day = False

    for pattern, warning in unsupported:
        if re.search(pattern, text, flags=re.IGNORECASE):
            if warning.endswith("last business day."):
                matched_last_business_day = True
            if matched_last_business_day and warning.endswith("business days."):
                continue
            warnings.append(warning)

    return warnings


def _unique_warnings(warnings):
    unique = []
    seen = set()

    for warning in warnings:
        if warning in seen:
            continue

        seen.add(warning)
        unique.append(warning)

    return unique


def _clean_title(text):
    title = str(text or "").strip()
    patterns = [
        rf"\bevery\s+year\s+on\s+(?:{_month_names_pattern()})\s+\d{{1,2}}(?:st|nd|rd|th)?\b",
        r"\bevery\s+month\s+on\s+the\s+\d{1,2}(?:st|nd|rd|th)?\b",
        r"\bevery\s+month\s+on\s+\d{1,2}(?:st|nd|rd|th)?\b",
        rf"\bevery\s+week\s+on\s+(?:{_weekday_names_pattern()})(?:\s+and\s+(?:{_weekday_names_pattern()}))*\b",
        rf"\bevery\s+(?:{_weekday_names_pattern()})(?:\s+and\s+(?:{_weekday_names_pattern()}))*\b",
        r"\bevery\s+day\b",
        r"\bdaily\b",
        r"\bmonthly\b",
        r"\byearly\b",
    ]

    for pattern in patterns:
        title = re.sub(pattern, " ", title, flags=re.IGNORECASE)

    title = re.sub(r"\s+", " ", title).strip()
    title = title.strip(" -.,;:")
    return title or str(text or "").strip()


def _parse_rule(text, anchor):
    lowered = str(text or "").strip().lower()
    recurring_task = {
        "title": _clean_title(text),
        "frequency": "",
        "interval": 1,
        "days_of_week": [],
        "day_of_month": None,
        "month_of_year": None,
        "start_date": "",
        "category": classify_category(text),
        "priority": parse_priority_from_text(text),
        "project": "",
    }

    month_pattern = _month_names_pattern()
    yearly_match = re.search(
        rf"\bevery\s+year\s+on\s+({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
        lowered,
        flags=re.IGNORECASE,
    )
    if yearly_match:
        recurring_task.update({
            "frequency": "yearly",
            "month_of_year": MONTHS[yearly_match.group(1).lower()],
            "day_of_month": int(yearly_match.group(2)),
        })
        return recurring_task, []

    monthly_match = re.search(
        r"\bevery\s+month\s+on\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\b",
        lowered,
        flags=re.IGNORECASE,
    )
    if monthly_match:
        day = _ordinal_day(monthly_match.group(1))
        if not day:
            return recurring_task, ["Unsupported monthly day."]
        recurring_task.update({"frequency": "monthly", "day_of_month": day})
        return recurring_task, []

    if re.search(r"\bmonthly\b|\bevery\s+month\b", lowered):
        recurring_task.update({"frequency": "monthly", "day_of_month": anchor.day})
        return recurring_task, ["No monthly day was provided; using anchor_date day."]

    if re.search(r"\bdaily\b|\bevery\s+day\b", lowered):
        recurring_task["frequency"] = "daily"
        return recurring_task, []

    weekday_names = _extract_weekdays(lowered)
    if weekday_names and (
        re.search(r"\bevery\s+week\b", lowered)
        or re.search(rf"\bevery\s+(?:{_weekday_names_pattern()})", lowered)
    ):
        recurring_task.update({
            "frequency": "weekly",
            "days_of_week": weekday_names,
        })
        return recurring_task, []

    if re.search(r"\bweekly\b|\bevery\s+week\b", lowered):
        recurring_task.update({
            "frequency": "weekly",
            "days_of_week": [anchor.strftime("%A").lower()],
        })
        return recurring_task, ["No weekday was provided; using anchor_date weekday."]

    if re.search(r"\byearly\b|\bevery\s+year\b", lowered):
        recurring_task.update({
            "frequency": "yearly",
            "month_of_year": anchor.month,
            "day_of_month": anchor.day,
        })
        return recurring_task, ["No yearly month/day was provided; using anchor_date."]

    return recurring_task, ["No supported recurrence pattern was found."]


def _daily_occurrences(anchor, horizon_days):
    end_date = anchor + timedelta(days=horizon_days)
    current = anchor
    occurrences = []

    while current <= end_date:
        occurrences.append(current)
        current += timedelta(days=1)

    return occurrences


def _weekly_occurrences(anchor, horizon_days, days_of_week):
    wanted = {WEEKDAYS[day] for day in days_of_week if day in WEEKDAYS}
    end_date = anchor + timedelta(days=horizon_days)
    current = anchor
    occurrences = []

    while current <= end_date:
        if current.weekday() in wanted:
            occurrences.append(current)
        current += timedelta(days=1)

    return occurrences


def _monthly_occurrences(anchor, horizon_days, day_of_month):
    end_date = anchor + timedelta(days=horizon_days)
    year = anchor.year
    month = anchor.month
    occurrences = []

    while True:
        candidate = _safe_date(year, month, day_of_month)
        if candidate > end_date:
            break
        if candidate >= anchor:
            occurrences.append(candidate)
        year, month = _next_month(year, month)

    return occurrences


def _yearly_occurrences(anchor, horizon_days, month_of_year, day_of_month):
    end_date = anchor + timedelta(days=horizon_days)
    occurrences = []
    year = anchor.year

    while True:
        candidate = _safe_date(year, month_of_year, day_of_month)
        if candidate > end_date:
            break
        if candidate >= anchor:
            occurrences.append(candidate)
        year += 1

    return occurrences


def _build_occurrences(rule, anchor, horizon_days):
    frequency = rule.get("frequency")

    if frequency == "daily":
        dates = _daily_occurrences(anchor, horizon_days)
    elif frequency == "weekly":
        dates = _weekly_occurrences(anchor, horizon_days, rule.get("days_of_week") or [])
    elif frequency == "monthly":
        dates = _monthly_occurrences(anchor, horizon_days, rule.get("day_of_month"))
    elif frequency == "yearly":
        dates = _yearly_occurrences(
            anchor,
            horizon_days,
            rule.get("month_of_year"),
            rule.get("day_of_month"),
        )
    else:
        dates = []

    return [
        {
            "due_date": occurrence.isoformat(),
            "task_title": rule.get("title"),
            "would_create_task": False,
        }
        for occurrence in dates
    ]


def build_recurring_task_preview(
    text,
    project="",
    timezone=DEFAULT_TIMEZONE,
    anchor_date=None,
    horizon_days=DEFAULT_HORIZON_DAYS,
):
    unsupported_warnings = _has_unsupported_pattern(text)
    warnings = unsupported_warnings.copy()
    anchor, anchor_warning = _parse_anchor_date(anchor_date)
    horizon, horizon_warning = _clamp_horizon_days(horizon_days)

    for warning in (anchor_warning, horizon_warning):
        if warning:
            warnings.append(warning)

    recurring_task, rule_warnings = _parse_rule(text, anchor)
    recurring_task["project"] = str(project or "").strip()
    recurring_task["timezone"] = str(timezone or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE

    if unsupported_warnings:
        recurring_task["frequency"] = recurring_task.get("frequency") or ""
        occurrences = []
    else:
        warnings.extend(rule_warnings)
        occurrences = _build_occurrences(recurring_task, anchor, horizon)

    if occurrences:
        recurring_task["start_date"] = occurrences[0]["due_date"]
    elif recurring_task.get("frequency") and not unsupported_warnings:
        warnings.append("No occurrences found within the requested preview horizon.")

    warnings = _unique_warnings(warnings)

    return {
        "dry_run": True,
        "creates_tasks": False,
        "schema_changes": False,
        "recurring_task": recurring_task,
        "occurrences": occurrences,
        "warnings": warnings,
        "metadata": {
            "anchor_date": anchor.isoformat(),
            "horizon_days": horizon,
            "preview_only": True,
        },
    }
