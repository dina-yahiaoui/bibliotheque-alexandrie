import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest.fetch import load_config


def index_chunks(chunks_file, collection_name, model, client):
    """Transforme les passages en vecteurs et les range dans une collection Chroma."""
    chunks = json.loads(Path(chunks_file).read_text(encoding="utf-8"))

    # On repart de zéro : si la collection existe déjà, on la supprime
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(collection_name)

    # 1. Transformer tous les textes en vecteurs
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    # 2. Les ranger dans Chroma, avec leur fiche
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=vectors.tolist(),
        documents=texts,
        metadatas=[
            {"source_url": c["source_url"], "page_title": c["page_title"], "section": c["section"]}
            for c in chunks
        ],
    )
    print(f"{collection.count()} passages indexés dans '{collection_name}'")


def main():
    config = load_config()
    model = SentenceTransformer(config["embeddings"]["model"])
    client = chromadb.PersistentClient(path=config["vector_db"]["path"])

    for size in config["chunking"]["sizes"]:
        index_chunks(
            chunks_file=f"data/chunks_{size}.json",
            collection_name=f"{config['corpus']['name']}_{size}",
            model=model,
            client=client,
        )


if __name__ == "__main__":
    main()