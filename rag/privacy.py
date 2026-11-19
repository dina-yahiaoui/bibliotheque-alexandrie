import re

# Motif à repérer → texte de remplacement
PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"(?:\+33\s?|0)[1-9](?:[\s.-]?\d{2}){4}"), "[TÉLÉPHONE]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"), "[CLÉ_API]"),
]


def mask_personal_data(text):
    """Remplace les e-mails, téléphones et clés API par des étiquettes, avant tout envoi externe."""
    for pattern, label in PATTERNS:
        text = pattern.sub(label, text)
    return text

PLACEHOLDERS = re.compile(r"\[(?:EMAIL|TÉLÉPHONE|CLÉ_API)\]")

# Formule de présentation autour d'une étiquette : "Je suis [EMAIL],", "mon e-mail est [EMAIL]."...
INTRO = re.compile(
    r"\b(?:je suis|je m'appelle|c'est|mon (?:e-?mail|adresse|mail|numéro|téléphone|tel) est)\s*"
    r"\[(?:EMAIL|TÉLÉPHONE|CLÉ_API)\]\s*[,.;:]?",
    re.IGNORECASE,
)


def remove_placeholders(text):
    """Retire les étiquettes de masquage, qui perturbent la recherche de passages."""
    text = INTRO.sub("", text)          # d'abord la formule entière ("Je suis [EMAIL],")
    text = PLACEHOLDERS.sub("", text)   # puis les étiquettes restantes, seules
    return re.sub(r"\s{2,}", " ", text).strip()   # enlève les doubles espaces laissés