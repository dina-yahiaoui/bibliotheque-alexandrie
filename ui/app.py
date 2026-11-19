import gradio as gr
import requests

API_URL = "http://127.0.0.1:8000"


def ask_question(question):
    """Envoie la question à l'API et met en forme la réponse pour l'affichage."""
    if not question or len(question.strip()) < 3:
        return "⚠️ Écris une question d'au moins 3 caractères.", ""

    try:
        response = requests.post(f"{API_URL}/question", json={"question": question}, timeout=120)
    except requests.ConnectionError:
        return "❌ L'assistant ne répond pas. Vérifie que l'API est lancée (`uvicorn api.main:app`).", ""

    if response.status_code != 200:
        return f"❌ Erreur {response.status_code} : {response.text}", ""

    data = response.json()

    if data["sources"]:
        lines = [f"- **[{s['num']}]** [{s['page_title']} › {s['section']}]({s['url']})" for s in data["sources"]]
        sources_md = "### 📎 Sources\n" + "\n".join(lines)
    else:
        sources_md = "### 📎 Sources\n_Aucune source._"

    sources_md += f"\n\n⏱️ Temps de réponse : {data['response_time']} s"
    return data["answer"], sources_md


def load_stats():
    """Récupère les statistiques auprès de l'API et les met en forme (2 tableaux Markdown)."""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=10)
    except requests.ConnectionError:
        return "❌ Impossible de charger les statistiques : l'API ne répond pas. Vérifie qu'elle est lancée (`uvicorn api.main:app`).", ""

    if response.status_code != 200:
        return f"❌ Erreur {response.status_code} : {response.text}", ""

    s = response.json()
    if s["total_questions"] == 0:
        return "_Aucune question posée pour le moment (ou toutes datent de plus de 30 jours)._", ""

    indicators = (
        "### 📈 Indicateurs (30 derniers jours)\n"
        "| Indicateur | Valeur |\n"
        "|---|---|\n"
        f"| Nombre de questions | {s['total_questions']} |\n"
        f"| Temps de réponse moyen | {s['avg_response_time']} s |\n"
        f"| Temps de réponse max | {s['max_response_time']} s |\n"
        f"| Passages envoyés au modèle (moyenne) | {s['avg_passages']} |\n"
        f"| Sources citées (moyenne) | {s['avg_sources']} |\n"
        f"| Taux de « je ne sais pas » | {s['idk_rate']} % |\n"
        f"| Réponses venant du cache | {s['cache_rate']} % |\n"
        f"| Déclenchements du garde-fou | {s['guard_triggered_count']} |\n"
        f"| Questions avec données masquées | {s['masked_count']} |"
    )

    lines = [
        f"| {q['created_at'].replace('T', ' ')} | {q['response_time']} s | {q['nb_passages']} | "
        f"{q['nb_sources']} | {'✅ oui' if q['is_idk'] else 'non'} |"
        for q in s["last_questions"]
    ]
    last = (
        "### 🕒 10 dernières questions\n"
        "_🔒 Le texte des questions et des réponses n'est jamais enregistré : seulement ces chiffres._\n\n"
        "| Date | Temps | Passages | Sources | Je ne sais pas |\n"
        "|---|---|---|---|---|\n" + "\n".join(lines)
    )
    return indicators, last


with gr.Blocks(title="La Bibliothèque d'Alexandrie") as demo:
    gr.Markdown(
        "# 📚 La Bibliothèque d'Alexandrie\n"
        "Pose une question sur la documentation : l'assistant répond **uniquement** à partir de la doc "
        "et **cite ses sources**. S'il ne trouve pas la réponse, il te le dit."
    )

    # ---------- Onglet 1 : poser une question ----------
    with gr.Tab("💬 Poser une question"):
        gr.Markdown(
            "> 🔒 **Confidentialité** : pour générer la réponse, ta question est envoyée à **OpenAI** (États-Unis), "
            "avec des extraits de la documentation. Les **e-mails, numéros de téléphone et clés API sont masqués** "
            "avant l'envoi. Nous **n'enregistrons pas le texte** de ta question : seulement des statistiques anonymes "
            "(temps de réponse, nombre de passages, « je ne sais pas »), supprimées après **30 jours**. "
            "Merci de ne pas écrire d'informations personnelles (nom, adresse…)."
        )
        question = gr.Textbox(label="Ta question", placeholder="Ex : Comment rendre un paramètre de requête optionnel ?")
        send_button = gr.Button("Envoyer", variant="primary")

        answer = gr.Markdown()
        sources = gr.Markdown()

        # Clic sur le bouton OU touche Entrée → même action
        send_button.click(ask_question, inputs=question, outputs=[answer, sources])
        question.submit(ask_question, inputs=question, outputs=[answer, sources])

    # ---------- Onglet 2 : statistiques ----------
    with gr.Tab("📊 Statistiques"):
        refresh_button = gr.Button("🔄 Actualiser")
        indicators = gr.Markdown()
        last_questions = gr.Markdown()

        refresh_button.click(load_stats, outputs=[indicators, last_questions])

    # Les stats sont aussi chargées à l'ouverture de la page
    demo.load(load_stats, outputs=[indicators, last_questions])


if __name__ == "__main__":
    demo.launch(inbrowser=True)
