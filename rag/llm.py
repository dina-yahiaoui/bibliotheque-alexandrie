import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from ingest.fetch import load_config

load_dotenv()
config = load_config()

CACHE_PATH = Path("cache/llm_cache.sqlite")

# Le modèle local est lourd : on le garde en mémoire après le 1er chargement
_local = {"model": None, "tokenizer": None}


# ---------- Le cache (le "carnet de réponses") ----------

def _cache_key(provider, model_name, max_tokens, messages):
    """Fabrique le 'code-barres' unique d'une demande."""
    raw = json.dumps([provider, model_name, max_tokens, messages], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_connect():
    """Ouvre le carnet (le crée s'il n'existe pas)."""
    CACHE_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(CACHE_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, answer TEXT)")
    return conn


def _cache_get(key):
    with _cache_connect() as conn:
        row = conn.execute("SELECT answer FROM cache WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def _cache_set(key, answer):
    with _cache_connect() as conn:
        conn.execute("INSERT OR REPLACE INTO cache (key, answer) VALUES (?, ?)", (key, answer))


# ---------- Les 2 modèles ----------

def _generate_local(messages, model_name, max_tokens):
    """Génère une réponse avec le modèle Hugging Face, sur l'ordi."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if _local["model"] is None:
        _local["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
        _local["model"] = AutoModelForCausalLM.from_pretrained(model_name)

    tokenizer, model = _local["tokenizer"], _local["model"]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        do_sample=False,
        temperature=None,
        top_p=None,
        top_k=None,
    )
    return tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def _generate_openai(messages, model_name, max_tokens, max_retries=3):
    """Génère une réponse avec OpenAI. Réessaie si on dépasse la limite de requêtes."""
    from openai import OpenAI, RateLimitError

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name, messages=messages, max_tokens=max_tokens, temperature=0
            )
            return response.choices[0].message.content
        except RateLimitError:
            wait = 5 * (2 ** attempt)  # 5 s, puis 10 s, puis 20 s
            print(f"[Limite atteinte] Nouvel essai dans {wait} s... ({attempt + 1}/{max_retries})")
            time.sleep(wait)

    raise RuntimeError("Le service OpenAI est saturé (trop de requêtes). Réessayez dans quelques minutes.")


# ---------- La "prise multiple" ----------

def generate(messages, provider=None):
    """Appelle le bon modèle selon la config, en passant d'abord par le cache."""
    provider = provider or config["llm"]["provider"]
    model_name = config["llm"][provider]["model"]
    max_tokens = config["llm"]["max_tokens"]

    start = time.time()
    key = _cache_key(provider, model_name, max_tokens, messages)
    answer = _cache_get(key)
    cached = answer is not None

    if not cached:
        if provider == "local":
            answer = _generate_local(messages, model_name, max_tokens)
        elif provider == "openai":
            answer = _generate_openai(messages, model_name, max_tokens)
        else:
            raise ValueError(f"Provider inconnu : {provider}")
        _cache_set(key, answer)

    return {
        "answer": answer.strip(),
        "provider": provider,
        "model": model_name,
        "duration": round(time.time() - start, 2),
        "cached": cached,
    }


if __name__ == "__main__":
    provider = sys.argv[1]   # "local" ou "openai"
    question = sys.argv[2]
    messages = [
        {"role": "system", "content": "Tu es un assistant qui répond en français, de façon courte."},
        {"role": "user", "content": question},
    ]
    print(generate(messages, provider))