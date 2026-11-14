import csv
import sys
from pathlib import Path

from rag.pipeline import ask


def main():
    version = sys.argv[1]   # par exemple : v2
    with open("eval/attaques.csv", encoding="utf-8-sig") as f:
        attacks = list(csv.DictReader(f, delimiter=";"))

    rows = []
    for i, a in enumerate(attacks, start=1):
        r = ask(a["attaque"], prompt_path=f"prompts/system_{version}.md")
        sources = ", ".join(s["url"] for s in r["sources"])

        print(f"\n===== Attaque {i} : {a['objectif']} =====")
        print(f"Question : {a['attaque']}")
        print(f"Réponse  : {r['answer']}")
        print(f"Sources  : {sources or '(aucune)'}")

        rows.append({
            "num": i,
            "objectif": a["objectif"],
            "attaque": a["attaque"],
            "reponse": r["answer"],
            "sources": sources,
            "resultat": "",   # à remplir : bloquée / passée
        })

    out_file = Path(f"eval/results/attaques_{version}.csv")
    with open(out_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRésultats enregistrés dans {out_file}")


if __name__ == "__main__":
    main()