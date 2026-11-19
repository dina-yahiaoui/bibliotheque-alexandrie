"""Lance l'assistant en une seule commande : python run.py

1. vérifie les prérequis (.env, base vectorielle, port 8000 libre) ;
2. démarre l'API (FastAPI) en arrière-plan et attend qu'elle soit prête ;
3. démarre l'interface (Gradio) qui s'ouvre dans le navigateur ;
4. Ctrl + C arrête proprement les deux.
"""
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
API_HOST, API_PORT = "127.0.0.1", 8000
API_URL = f"http://{API_HOST}:{API_PORT}"
UI_URL = "http://127.0.0.1:7860"
API_TIMEOUT = 120  # secondes : le modèle d'embeddings est long à charger


# ---------- 1. Vérification des prérequis ----------

def check_prerequisites(root=ROOT):
    """Renvoie un message d'erreur (texte) s'il manque quelque chose, sinon None."""
    if not (root / ".env").exists():
        return (
            "❌ Le fichier .env est introuvable.\n"
            "   → Copie le modèle :   copy .env.example .env\n"
            "   → Puis ouvre .env et mets ta clé :   OPENAI_API_KEY=sk-..."
        )

    with open(root / "config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    vector_db = root / config["vector_db"]["path"]
    if not vector_db.exists() or not any(vector_db.iterdir()):
        return (
            f"❌ La base vectorielle est introuvable (dossier « {config['vector_db']['path']} »).\n"
            "   → Lance ces 3 commandes, dans cet ordre :\n"
            "       python -m ingest.fetch\n"
            "       python -m ingest.chunk\n"
            "       python -m ingest.index"
        )
    return None


def port_in_use(host, port):
    """Vrai si un programme écoute déjà sur ce port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


# ---------- 2. Démarrage et arrêt des processus ----------

def wait_for_api(api_process):
    """Interroge GET /health jusqu'à ce que l'API réponde. Renvoie True si elle est prête."""
    start = time.time()
    while time.time() - start < API_TIMEOUT:
        if api_process.poll() is not None:  # l'API s'est arrêtée toute seule (erreur au démarrage)
            return False
        try:
            if requests.get(f"{API_URL}/health", timeout=2).status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    return False


def stop(process, name):
    """Arrête un processus s'il tourne encore (d'abord gentiment, puis de force)."""
    if process is None or process.poll() is not None:
        return
    print(f"   Arrêt de {name}...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main():
    os.chdir(ROOT)  # config.yaml, chroma_db/... sont lus depuis la racine du projet

    error = check_prerequisites()
    if error:
        print(error)
        sys.exit(1)

    if port_in_use(API_HOST, API_PORT):
        print(
            f"❌ Le port {API_PORT} est déjà utilisé : l'API est sans doute déjà lancée dans un autre terminal.\n"
            "   → Ferme ce terminal (ou fais Ctrl + C dedans), puis relance :   python run.py"
        )
        sys.exit(1)

    # Sous Windows, on transforme aussi Ctrl + Pause (CTRL_BREAK) en arrêt propre
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.default_int_handler)

    api_process = ui_process = None
    try:
        print("🚀 Démarrage de l'API (chargement du modèle, jusqu'à 2 minutes)", end="", flush=True)
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", API_HOST, "--port", str(API_PORT)]
        )
        if not wait_for_api(api_process):
            print(
                f"\n❌ L'API ne répond pas après {API_TIMEOUT} s (ou s'est arrêtée).\n"
                "   → Regarde les messages d'erreur au-dessus, puis relance :   python run.py"
            )
            sys.exit(1)
        print("\n✅ API prête.")

        print("🚀 Démarrage de l'interface...")
        ui_process = subprocess.Popen([sys.executable, "-m", "ui.app"])
        print(
            f"\n📚 La Bibliothèque d'Alexandrie est prête : {UI_URL}\n"
            "   (le navigateur va s'ouvrir tout seul)\n"
            "   Pour tout arrêter : Ctrl + C dans ce terminal.\n"
        )

        # On attend : si l'interface ou l'API s'arrête, on arrête tout
        while ui_process.poll() is None and api_process.poll() is None:
            time.sleep(1)
        print("⚠️ L'API ou l'interface s'est arrêtée de façon inattendue.")

    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé (Ctrl + C).")
    finally:
        # Quoi qu'il arrive : on ne laisse aucun processus en arrière-plan
        stop(ui_process, "l'interface")
        stop(api_process, "l'API")
        print("👋 Tout est arrêté.")


if __name__ == "__main__":
    main()
