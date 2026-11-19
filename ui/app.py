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


with gr.Blocks(title="La Bibliothèque d'Alexandrie") as demo:
    gr.Markdown(
        "# 📚 La Bibliothèque d'Alexandrie\n"
        "Pose une question sur la documentation : l'assistant répond **uniquement** à partir de la doc "
        "et **cite ses sources**. S'il ne trouve pas la réponse, il te le dit."
    )
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


if __name__ == "__main__":
    demo.launch()