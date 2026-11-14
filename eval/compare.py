import csv
from pathlib import Path

VERSIONS = ["v1", "v2"]


def load(version):
    with open(f"eval/results/answers_{version}.csv", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def count(rows, column, value="oui"):
    return sum(r[column] == value for r in rows)


def main():
    data = {v: load(v) for v in VERSIONS}
    n = len(data[VERSIONS[0]])

    metrics = [
        ("Réponse correcte", lambda rows: count(rows, "correcte")),
        ("Réponse partielle", lambda rows: count(rows, "correcte", "partiel")),
        ("Sources exactes", lambda rows: count(rows, "sources_ok")),
        ("Refus approprié", lambda rows: count(rows, "refus_ok")),
    ]

    lines = ["| Critère | " + " | ".join(VERSIONS) + " |", "|---|" + "---|" * len(VERSIONS)]
    for name, fn in metrics:
        lines.append(f"| {name} | " + " | ".join(f"{fn(data[v])}/{n}" for v in VERSIONS) + " |")

    table = "\n".join(lines)
    print(table)
    Path("eval/results/comparaison.md").write_text("# Comparaison des versions\n\n" + table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()