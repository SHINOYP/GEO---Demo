"""Database initialisation and session helpers (SQLite via aiosqlite)."""

import aiosqlite
import json
import os
import logging

logger = logging.getLogger("citelytics.db")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "citelytics.db")

CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    score       REAL,
    prediction  TEXT,
    features    TEXT,
    shap_values TEXT,
    recommendations TEXT
)
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_HISTORY)
        await db.commit()
    logger.info("Database ready at %s", DB_PATH)


async def save_analysis(url, timestamp, score, prediction, features, shap_values, recommendations):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO analysis_history
               (url, timestamp, score, prediction, features, shap_values, recommendations)
               VALUES (?,?,?,?,?,?,?)""",
            (
                url, timestamp, score, prediction,
                json.dumps(features),
                json.dumps(shap_values),
                json.dumps(recommendations),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_history():
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, url, timestamp, score, prediction FROM analysis_history ORDER BY id DESC LIMIT 100"
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_history_by_id(record_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM analysis_history WHERE id=?", (record_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    r = dict(row)
    r["features"] = json.loads(r["features"] or "{}")
    r["shap_values"] = json.loads(r["shap_values"] or "{}")
    r["recommendations"] = json.loads(r["recommendations"] or "[]")
    return r
