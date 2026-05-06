import re


HIGH_PRIORITY_PATTERNS = [
    r"\burgent\b",
    r"\basap\b",
    r"\bimportant\b",
    r"\bcritical\b",
    r"\bhigh priority\b",
    r"\btoday\b",
]

LOW_PRIORITY_PATTERNS = [
    r"\blow priority\b",
    r"\blater\b",
    r"\bsomeday\b",
    r"\bwhen possible\b",
    r"\bnot urgent\b",
]


def parse_priority_from_text(text: str) -> str:
    t = text.lower()

    for pattern in LOW_PRIORITY_PATTERNS:
        if re.search(pattern, t):
            return "Low"

    for pattern in HIGH_PRIORITY_PATTERNS:
        if re.search(pattern, t):
            return "High"

    return "Medium"
