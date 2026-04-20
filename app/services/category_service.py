def classify_category(text: str) -> str:
    t = text.lower()

    business_keywords = [
        "client", "meeting", "invoice", "project",
        "bug", "fix", "deploy", "code", "email",
        "kouch", "task", "work", "report"
    ]

    personal_keywords = [
        "buy", "gym", "call", "family",
        "doctor", "home", "clean", "shopping",
        "groceries"
    ]

    for word in business_keywords:
        if word in t:
            return "Business"

    for word in personal_keywords:
        if word in t:
            return "Personal"

    return "Unclear"