import csv
import sys
from pathlib import Path

from rag.llm import config
from rag.pipeline import ask


def load_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def yes_no(value):
    return "oui" if value else "non"


def main():
    version = sys.argv[1]                         # par exemple : v1
    prompt_path = f"prompts/system_{version}.md"
    base = config["corpus"]["site_base_url"]

    # 20 questions dans le corpus + 5 hors corpus (page attendue vide)
    questions = [(q["question"], q["page_attendue"]) for q in load_csv("eval/questions.csv")]
    questions += [(q["question"], "") for q in load_csv("eval/questions_hors_corpus.csv")]

    rows = []
    for i, (question, expected) in enumerate(questions, start=1):
        r = ask(question, prompt_path=prompt_path)
        cited = [s["url"].removeprefix(base) for s in r["sources"]]

        if expected:  # la réponse EST dans la doc
            refus_ok = not r["is_idk"]          # il fallait répondre
            sources_ok = expected in cited      # la bonne page doit être citée
            correcte = ""                       # à noter à la main
        else:         # la réponse N'EST PAS dans la doc
            refus_ok = r["is_idk"]              # il fallait refuser
            sources_ok = len(cited) == 0        # aucune source ne doit être citée
            correcte = yes_no(r["is_idk"])      # refuser = la bonne réponse

        rows.append({
            "num": i,
            "type": "corpus" if expected else "hors_corpus",
            "question": question,
            "page_attendue": expected,
            "reponse": r["answer"],
            "sources_citees": ", ".join(cited),
            "correcte": correcte,
            "sources_ok": yes_no(sources_ok),
            "refus_ok": yes_no(refus_ok),
            "duree_s": r["duration"],
        })
        print(f"[{i}/{len(questions)}] sources_ok={yes_no(sources_ok)} refus_ok={yes_no(refus_ok)}  {question}")

    out_file = Path(f"eval/results/answers_{version}.csv")
    with open(out_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRésultats enregistrés dans {out_file}")


if __name__ == "__main__":
    main()