from rag.pipeline import ask
from rag.privacy import remove_placeholders

q = "Je suis dina@gmail.com, comment recevoir un fichier envoyé par l'utilisateur ?"
r = ask(q)

print("Question après masquage :", r["question"])
print("Texte utilisé pour la recherche :", remove_placeholders(r["question"]))
print("Masquée :", r["masked"], "| Garde-fou déclenché :", r["guard_triggered"], "| Cache :", r["cached"])
print("Réponse :", r["answer"])
print("\nPassages réellement envoyés au LLM par ask() :")
for i, url in enumerate(r["passages_urls"], start=1):
    print(f"[{i}]", url)
print("\nSources citées :")
for s in r["sources"]:
    print(f"[{s['num']}]", s["url"], "|", s["section"])
