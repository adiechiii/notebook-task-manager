import re


MEMORY_TYPES = {
    "preference": "Preference",
    "person": "Person",
    "project": "Project",
    "business": "Business",
    "finance": "Finance",
    "trading": "Trading",
    "family": "Family",
    "instruction": "Instruction",
    "general": "General",
}

TYPE_PATTERNS = [
    (
        "Project",
        [
            r"\bproject\b",
            r"\brepo\b",
            r"\bbranch\b",
            r"\bapi\b",
            r"\bendpoint\b",
            r"\bphase\b",
            r"\bdeploy\b",
            r"\bbackend\b",
            r"\bfrontend\b",
        ],
        ["project"],
    ),
    (
        "Instruction",
        [
            r"\balways\b",
            r"\bnever\b",
            r"\bremember to\b",
            r"\bwhen i ask\b",
            r"\bdefault to\b",
            r"\bmake sure\b",
            r"\bdo not\b",
            r"\bdon't\b",
            r"\bshould\b",
            r"\bmust\b",
        ],
        ["instruction"],
    ),
    (
        "Preference",
        [
            r"\bprefers?\b",
            r"\blikes?\b",
            r"\bdislikes?\b",
            r"\bfavou?rites?\b",
            r"\bwants?\b",
            r"\bdoes not like\b",
        ],
        ["preference"],
    ),
    (
        "Trading",
        [
            r"\btrading\b",
            r"\btrade\b",
            r"\bcrypto\b",
            r"\bstocks?\b",
            r"\bforex\b",
            r"\bchart\b",
            r"\bmarket\b",
            r"\bbot\b",
            r"\bstrategy\b",
            r"\bwebhook\b",
        ],
        ["trading"],
    ),
    (
        "Finance",
        [
            r"\brent\b",
            r"\bbank\b",
            r"\binvoices?\b",
            r"\bpayments?\b",
            r"\bbills?\b",
            r"\bstatements?\b",
            r"\btax\b",
            r"\bmoney\b",
            r"\bsalary\b",
            r"\bexpenses?\b",
        ],
        ["finance"],
    ),
    (
        "Family",
        [
            r"\bmom\b",
            r"\bdad\b",
            r"\bfamily\b",
            r"\bwife\b",
            r"\bhusband\b",
            r"\bbrothers?\b",
            r"\bsisters?\b",
            r"\bkids?\b",
            r"\bchildren\b",
        ],
        ["family"],
    ),
    (
        "Business",
        [
            r"\bbusiness\b",
            r"\bcustomers?\b",
            r"\bsales\b",
            r"\bamazon\b",
            r"\bsuppliers?\b",
            r"\borders?\b",
            r"\bvendors?\b",
            r"\bclients?\b",
            r"\bwhatsapp group\b",
        ],
        ["business"],
    ),
]

TAG_PATTERNS = [
    ("family", r"\bmom\b|\bdad\b|\bfamily\b|\bwife\b|\bhusband\b|\bbrothers?\b|\bsisters?\b|\bkids?\b|\bchildren\b"),
    ("trading", r"\btrading\b|\btrade\b|\bcrypto\b|\bstocks?\b|\bforex\b|\bchart\b|\bmarket\b|\bbot\b|\bstrategy\b|\bwebhook\b"),
    ("whatsapp", r"\bwhatsapp\b"),
    ("email", r"\bemail\b"),
    ("communication", r"\bwhatsapp\b|\bemail\b|\bupdates?\b"),
    ("invoice", r"\binvoices?\b"),
    ("payment", r"\bpayments?\b|\bbills?\b"),
    ("api", r"\bapi\b|\bendpoints?\b"),
    ("repo", r"\brepo\b|\bbranch\b"),
    ("phase", r"\bphase\b"),
    ("security", r"\bpassword\b|\bsecret\b|\bcredential\b|\btoken\b"),
    ("deadline", r"\bdeadline\b|\bdue\b|\burgent\b"),
]

HIGH_IMPORTANCE_PATTERNS = [
    r"\balways\b",
    r"\bnever\b",
    r"\bmust\b",
    r"\bcritical\b",
    r"\burgent\b",
    r"\bpassword\b",
    r"\bsecret\b",
    r"\bcredential\b",
    r"\btoken\b",
    r"\btax\b",
    r"\bpayment\b",
    r"\bdeadline\b",
]

MEDIUM_TYPES = {
    "Preference",
    "Person",
    "Project",
    "Business",
    "Finance",
    "Trading",
    "Family",
    "Instruction",
}


def _normalize(text: str) -> str:
    return str(text or "").strip()


def _classification_text(text: str) -> str:
    return re.sub(
        r"^\s*(?:Phase\s+\d+(?:\.\d+)?\s+(?:test|final)|Memory classification final):\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []

    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)

    return result


def _extract_entity(text: str) -> str:
    patterns = [
        r"^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:prefers?|likes?|dislikes?|wants?|handles?|uses?|owns?|manages?|needs?)\b",
        r"\b(?:for|with|from|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return ""


def _extract_project(text: str) -> str:
    patterns = [
        r"\b(Phase\s+\d+(?:\.\d+)?)\b",
        r"\bproject\s+([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*)?)\b",
        r"\b([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*)*)\s+project\b",
        r"\brepo\s+([A-Za-z0-9_.-]+)\b",
        r"\bbranch\s+([A-Za-z0-9_./-]+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return ""


def _classify_type(text: str, lowered: str, entity: str) -> tuple[str, list[str]]:
    for memory_type, patterns, tags in TYPE_PATTERNS:
        if _matches(lowered, patterns):
            return memory_type, tags

    if entity:
        return "Person", ["person"]

    return "General", ["general"]


def _classify_importance(memory_type: str, lowered: str) -> str:
    if _matches(lowered, HIGH_IMPORTANCE_PATTERNS):
        return "High"

    if memory_type in MEDIUM_TYPES:
        return "Medium"

    return "Low"


def _classify_tags(lowered: str, base_tags: list[str]) -> str:
    tags = list(base_tags)

    for tag, pattern in TAG_PATTERNS:
        if re.search(pattern, lowered):
            tags.append(tag)

    return ", ".join(_dedupe(tags))


def classify_memory(text: str) -> dict:
    normalized = _classification_text(_normalize(text))
    lowered = normalized.lower()
    entity = _extract_entity(normalized)
    project = _extract_project(normalized)
    memory_type, base_tags = _classify_type(normalized, lowered, entity)

    if project and memory_type == "General":
        memory_type = "Project"
        base_tags = ["project"]

    return {
        "type": memory_type,
        "entity": entity,
        "project": project,
        "tags": _classify_tags(lowered, base_tags),
        "importance": _classify_importance(memory_type, lowered),
    }
