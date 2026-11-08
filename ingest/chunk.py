import html
import json
import re
from pathlib import Path

from ingest.fetch import load_config

def clean_markdown(text):
    """Enlève le 'bruit' technique des fichiers Markdown de FastAPI."""
    text = re.sub(r"\{\*.*?\*\}", "", text)                    # 1. inclusions de code
    text = re.sub(r"\s*\{\s*#[^}]*\}", "", text)               # 2. ancres de titres
    text = re.sub(r"^///.*$", "", text, flags=re.MULTILINE)    # 3. encadrés ///
    text = re.sub(r"<[^>]+>", "", text)                        # 4. balises HTML
    text = re.sub(r"\n{3,}", "\n\n", text) 
    text = html.unescape(text)                                 # 6. &apos; -> '                    # 5. lignes vides en trop
    return text.strip()


def split_by_sections(text):
    """Coupe le texte à chaque titre (#, ##, ###). Renvoie une liste de (titre, contenu)."""
    sections = []
    current_title = "Introduction"
    current_lines = []
    in_code = False

    for line in text.split("\n"):
        # Est-ce qu'on entre ou sort d'un bloc de code ?
        if line.strip().startswith("```"):
            in_code = not in_code

        # Est-ce un vrai titre ? (commence par #, ## ou ### ET pas dans du code)
        is_title = not in_code and re.match(r"^#{1,3} ", line)

        if is_title:
            # On range la section précédente avant d'en commencer une nouvelle
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Ne pas oublier la toute dernière section
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    # On enlève les sections vides
    return [(title, content) for title, content in sections if content]

def split_long_text(text, max_chars=800, overlap=100):
    """Coupe un texte trop long en morceaux d'environ max_chars, entre les paragraphes."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        # Si on ajoute ce paragraphe, est-ce que ça dépasse ?
        if current and len(current) + len(para) > max_chars:
            chunks.append(current.strip())                 # on ferme le carton
            current = current[-overlap:] + "\n\n" + para   # nouveau carton, avec la fin du précédent
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())                     # le dernier carton

    return chunks

def get_page_title(text, fallback):
    """Trouve le titre principal de la page (la ligne qui commence par '# ')."""
    match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def build_chunks(raw_dir, max_chars, overlap):
    """Découpe toutes les pages du manifest en passages, avec leur source."""
    manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    chunks = []

    for page in manifest:
        text = clean_markdown((raw_dir / page["file"]).read_text(encoding="utf-8"))
        page_title = get_page_title(text, page["file"])

        for section_title, content in split_by_sections(text):
            for piece in split_long_text(content, max_chars, overlap):
                chunks.append({
                    "id": f"{page['file']}#{len(chunks)}",
                    "text": f"{page_title} > {section_title}\n\n{piece}",
                    "source_url": page["source_url"],
                    "page_title": page_title,
                    "section": section_title,
                })
    return chunks


def main():
    config = load_config()
    raw_dir = Path(config["corpus"]["output_dir"])
    overlap = config["chunking"]["overlap"]

    for size in config["chunking"]["sizes"]:
        chunks = build_chunks(raw_dir, size, overlap)
        out_file = Path("data") / f"chunks_{size}.json"
        out_file.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

        average = sum(len(c["text"]) for c in chunks) // len(chunks)
        print(f"Taille {size} : {len(chunks)} passages (moyenne {average} caractères) -> {out_file}")


if __name__ == "__main__":
    main()
