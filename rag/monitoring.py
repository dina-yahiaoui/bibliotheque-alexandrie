import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("logs/monitoring.sqlite")
RETENTION_DAYS = 30  # RGPD : on ne garde pas les statistiques plus de 30 jours

# RÈGLE RGPD : aucune colonne pour le texte de la question ni pour la réponse
SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    response_time REAL NOT NULL,
    nb_passages INTEGER NOT NULL,
    nb_sources INTEGER NOT NULL,
    is_idk INTEGER NOT NULL,
    cached INTEGER NOT NULL,
    guard_triggered INTEGER NOT NULL,
    masked INTEGER NOT NULL,
    model TEXT
)
"""


def _connect():
    """Ouvre la base (la crée si besoin)."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def _purge_old(conn):
    """Supprime les lignes de plus de 30 jours (RGPD)."""
    limit = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    conn.execute("DELETE FROM logs WHERE created_at < ?", (limit,))


def log_question(result):
    """Enregistre UNE ligne de statistiques à partir du dictionnaire renvoyé par ask().
    On ne garde que des chiffres : jamais la question ni la réponse."""
    row = (
        datetime.now().isoformat(timespec="seconds"),
        result["duration"],
        result["nb_passages"],
        len(result["sources"]),
        int(result["is_idk"]),
        int(result["cached"]),
        int(result["guard_triggered"]),
        int(result["masked"]),
        result["model"],
    )
    with _connect() as conn:
        _purge_old(conn)
        conn.execute(
            "INSERT INTO logs (created_at, response_time, nb_passages, nb_sources, is_idk, "
            "cached, guard_triggered, masked, model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )


def get_stats():
    """Calcule les statistiques globales et renvoie les 10 dernières lignes."""
    with _connect() as conn:
        _purge_old(conn)
        total, avg_time, max_time, avg_passages, avg_sources, nb_idk, nb_cached, nb_guard, nb_masked = conn.execute(
            "SELECT COUNT(*), AVG(response_time), MAX(response_time), AVG(nb_passages), AVG(nb_sources), "
            "SUM(is_idk), SUM(cached), SUM(guard_triggered), SUM(masked) FROM logs"
        ).fetchone()
        last_rows = conn.execute(
            "SELECT created_at, response_time, nb_passages, nb_sources, is_idk "
            "FROM logs ORDER BY id DESC LIMIT 10"
        ).fetchall()

    # Cas « 0 question » : les AVG/SUM valent None, on renvoie des zéros
    if total == 0:
        return {
            "total_questions": 0,
            "avg_response_time": 0,
            "max_response_time": 0,
            "avg_passages": 0,
            "avg_sources": 0,
            "idk_rate": 0,
            "cache_rate": 0,
            "guard_triggered_count": 0,
            "masked_count": 0,
            "last_questions": [],
        }

    return {
        "total_questions": total,
        "avg_response_time": round(avg_time, 2),
        "max_response_time": round(max_time, 2),
        "avg_passages": round(avg_passages, 2),
        "avg_sources": round(avg_sources, 2),
        "idk_rate": round(100 * nb_idk / total, 1),
        "cache_rate": round(100 * nb_cached / total, 1),
        "guard_triggered_count": nb_guard,
        "masked_count": nb_masked,
        "last_questions": [
            {
                "created_at": r[0],
                "response_time": r[1],
                "nb_passages": r[2],
                "nb_sources": r[3],
                "is_idk": bool(r[4]),
            }
            for r in last_rows
        ],
    }
