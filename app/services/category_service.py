import re


CATEGORY_PATTERNS = {
    "Trading": [
        r"\btrading\b",
        r"\btrade\b",
        r"\bcrypto\b",
        r"\bstock\b",
        r"\bstocks\b",
        r"\bforex\b",
        r"\bchart\b",
        r"\bmarket\b",
        r"\bbot\b",
        r"\bstrategy\b",
        r"\bwebhook\b",
    ],
    "Finance": [
        r"\brent\b",
        r"\bbank\b",
        r"\binvoice\b",
        r"\binvoices\b",
        r"\bpayment\b",
        r"\bbill\b",
        r"\bbills\b",
        r"\bstatement\b",
        r"\bstatements\b",
        r"\btax\b",
        r"\bmoney\b",
        r"\bsalary\b",
        r"\bexpense\b",
    ],
    "Family": [
        r"\bmom\b",
        r"\bdad\b",
        r"\bfamily\b",
        r"\bwife\b",
        r"\bhusband\b",
        r"\bbrother\b",
        r"\bsister\b",
        r"\bkids\b",
        r"\bchild\b",
        r"\bchildren\b",
    ],
    "Business": [
        r"\bbusiness\b",
        r"\bcustomer\b",
        r"\bsales\b",
        r"\bamazon\b",
        r"\bsupplier\b",
        r"\border\b",
        r"\borders\b",
        r"\bvendor\b",
        r"\bwhatsapp group\b",
    ],
    "Work": [
        r"\bwork\b",
        r"\btask\b",
        r"\breport\b",
        r"\bemail\b",
        r"\bmeeting\b",
        r"\bclient\b",
        r"\bdeploy\b",
        r"\bbug\b",
        r"\bfix\b",
        r"\bcode\b",
        r"\bapi\b",
    ],
    "Shopping": [
        r"\bbuy\b",
        r"\bshopping\b",
        r"\bgroceries\b",
        r"\bmilk\b",
        r"\bsupermarket\b",
        r"\border\b",
    ],
    "Health": [
        r"\bgym\b",
        r"\bdoctor\b",
        r"\bhealth\b",
        r"\bmedicine\b",
        r"\bappointment\b",
        r"\bworkout\b",
        r"\bwalk\b",
    ],
    "Learning": [
        r"\bstudy\b",
        r"\blearn\b",
        r"\bcourse\b",
        r"\bread\b",
        r"\bresearch\b",
        r"\bpractice\b",
        r"\btutorial\b",
    ],
    "Home": [
        r"\bhome\b",
        r"\bclean\b",
        r"\bgarage\b",
        r"\blaundry\b",
        r"\bkitchen\b",
        r"\broom\b",
        r"\bhouse\b",
    ],
}


def classify_category(text: str) -> str:
    t = text.lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, t):
                return category

    return "General"
