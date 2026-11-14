import re
import sys
import time
from pathlib import Path

from rag.llm import config, generate
from rag.retriever import search

IDK_PHRASE = "je ne sais pas"


def load_prompt(path=None):
    """Lit le fichier de consigne (par défaut celui de la config)."""
    return Path(path or config["llm"]["prompt"]).read_text(encoding="utf-8")


def build_context(passages):
    """Numérote les passages : [1] ..., [2] ..., [3] ..."""
    blocks = []
    for i, p in enumerate(passages, start=1):
        blocks.append(f"[{i}] {p['text']}")
    return "\n\n".join(blocks)


def extract_sources(answer, passages):
    """Repère les [1], [2]... cités dans la réponse et les transforme en vraies sources."""
    numbers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    sources = []
    for n in numbers:
        if 1 <= n <= len(passages):  # on ignore un numéro inventé, comme [7]
            p = passages[n - 1]
            sources.append({
                "num": n,
                "url": p["source_url"],
                "page_title": p["page_title"],
                "section": p["section"],
            })
    return sources


def ask(question, provider=None, prompt_path=None):
    """La chaîne complète : question -> recherche -> prompt -> réponse avec sources."""
    start = time.time()

    # 1. Recherche des passages
    passages = search(question, k=config["retrieval"]["k"], chunk_size=config["retrieval"]["chunk_size"])

    # 2. Construction du message pour le LLM
    messages = [
        {"role": "system", "content": load_prompt(prompt_path)},
        {"role": "user", "content": f"Passages :\n\n{build_context(passages)}\n\nQuestion : {question}"},
    ]

    # 3. Génération de la réponse
    result = generate(messages, provider)
    answer = result["answer"]
    is_idk = IDK_PHRASE in answer.lower()
    sources = [] if is_idk else extract_sources(answer, passages)

    # 4. Garde-fou : une réponse sans aucune source valide n'est pas affichée
    guard_triggered = not is_idk and not sources
    if guard_triggered:
        answer = "Je ne sais pas."
        is_idk = True

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "is_idk": is_idk,
        "guard_triggered": guard_triggered,
        "nb_passages": len(passages),
        "provider": result["provider"],
        "model": result["model"],
        "cached": result["cached"],
        "duration": round(time.time() - start, 2),
    }

if __name__ == "__main__":
    r = ask(sys.argv[1])
    print("\n=== RÉPONSE ===")
    print(r["answer"])
    print("\n=== SOURCES ===")
    for s in r["sources"]:
        print(f"[{s['num']}] {s['page_title']} > {s['section']}")
        print(f"    {s['url']}")
    if not r["sources"]:
        print("(aucune)")
    print(f"\n({r['provider']} / {r['model']} | {r['duration']} s | cache : {r['cached']} | je ne sais pas : {r['is_idk']})")