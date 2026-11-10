import sys

import chromadb
from sentence_transformers import SentenceTransformer

from ingest.fetch import load_config

# Chargés une seule fois, au démarrage
config = load_config()
model = SentenceTransformer(config["embeddings"]["model"])
client = chromadb.PersistentClient(path=config["vector_db"]["path"])


def search(question, k=3, chunk_size=500):
    """Renvoie les k passages les plus proches de la question, avec leur source."""
    collection = client.get_collection(f"{config['corpus']['name']}_{chunk_size}")

    question_vector = model.encode(question, normalize_embeddings=True)
    results = collection.query(query_embeddings=[question_vector.tolist()], n_results=k)

    passages = []
    for text, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        passages.append({
            "text": text,
            "source_url": meta["source_url"],
            "page_title": meta["page_title"],
            "section": meta["section"],
            "distance": round(distance, 3),
        })
    return passages


if __name__ == "__main__":
    question = sys.argv[1]
    for i, p in enumerate(search(question), start=1):
        print(f"--- Résultat {i} (distance {p['distance']}) ---")
        print(f"Page    : {p['page_title']} > {p['section']}")
        print(f"Source  : {p['source_url']}")
        print(f"Extrait : {p['text'][:200]}...")
        print()