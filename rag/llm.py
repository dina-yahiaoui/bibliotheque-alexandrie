import os
import sys
import time

from dotenv import load_dotenv

from ingest.fetch import load_config

load_dotenv()
config = load_config()

# Le modèle local est lourd : on le garde en mémoire après le 1er chargement
_local = {"model": None, "tokenizer": None}


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


def _generate_openai(messages, model_name, max_tokens):
    """Génère une réponse avec OpenAI, via Internet."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model_name, messages=messages, max_tokens=max_tokens, temperature=0
    )
    return response.choices[0].message.content


def generate(messages, provider=None):
    """La 'prise multiple' : appelle le bon modèle selon la config."""
    provider = provider or config["llm"]["provider"]
    model_name = config["llm"][provider]["model"]
    max_tokens = config["llm"]["max_tokens"]

    start = time.time()
    if provider == "local":
        answer = _generate_local(messages, model_name, max_tokens)
    elif provider == "openai":
        answer = _generate_openai(messages, model_name, max_tokens)
    else:
        raise ValueError(f"Provider inconnu : {provider}")

    return {
        "answer": answer.strip(),
        "provider": provider,
        "model": model_name,
        "duration": round(time.time() - start, 2),
    }


if __name__ == "__main__":
    provider = sys.argv[1]   # "local" ou "openai"
    question = sys.argv[2]
    messages = [
        {"role": "system", "content": "Tu es un assistant qui répond en français, de façon courte."},
        {"role": "user", "content": question},
    ]
    print(generate(messages, provider))