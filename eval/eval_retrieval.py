import csv
import json
from pathlib import Path

from rag.retriever import config, search

K = 3  # on regarde les 3 premiers résultats


def load_questions(path="eval/questions.csv"):
    """Lit le fichier des questions. Renvoie une liste de dictionnaires."""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def evaluate(questions, chunk_size):
    """Fait passer l'examen pour une taille de passage. Renvoie le score et le détail."""
    base = config["corpus"]["site_base_url"]
    details = []

    for q in questions:
        expected = q["page_attendue"]
        results = search(q["question"], k=K, chunk_size=chunk_size)
        found = [r["source_url"].removeprefix(base) for r in results]

        details.append({
            "question": q["question"],
            "attendu": expected,
            "trouves": found,
            "hit": expected in found,
        })

    score = sum(d["hit"] for d in details)
    return score, details


def main():
    questions = load_questions()

    for size in config["chunking"]["sizes"]:
        score, details = evaluate(questions, size)
        print(f"\n===== Taille {size} : {score}/{len(questions)} ({score / len(questions):.0%}) =====")

        for d in details:
            if d["hit"]:
                print(f"[OK]    {d['question']}")
            else:
                print(f"[RATÉ]  {d['question']}")
                print(f"          attendu : {d['attendu']}")
                print(f"          trouvé  : {d['trouves']}")

        out_file = Path("eval/results") / f"retrieval_{size}.json"
        out_file.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()