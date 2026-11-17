"""Synthetic playground examples; no production data."""

EXAMPLES = {
    "English — bank": {
        "text": "Sarah Al-Mansoor submitted a mortgage application to the National Bank of Egypt.",
        "span": "National Bank of Egypt",
        "entity_type": "BANK",
    },
    "English — person": {
        "text": "John Doe contacted the claims department about his mortgage application.",
        "span": "John Doe",
        "entity_type": "PERSON_NAME",
    },
    "Arabic — bank": {
        "text": "قدمت سارة المنصور طلب تمويل إلى البنك الأهلي المصري.",
        "span": "البنك الأهلي المصري",
        "entity_type": "BANK",
    },
    "Arabic — university": {
        "text": "يعمل أحمد في جامعة عين شمس منذ عام 2020.",
        "span": "جامعة عين شمس",
        "entity_type": "CORPORATION",
    },
}

