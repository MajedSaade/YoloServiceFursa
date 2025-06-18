import sqlite3
from storage.base import StorageInterface

class SQLiteStorage(StorageInterface):
    def __init__(self, db_path="predictions.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_sessions (
                    uid TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_image TEXT,
                    predicted_image TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detection_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_uid TEXT,
                    label TEXT,
                    score REAL,
                    box TEXT,
                    FOREIGN KEY (prediction_uid) REFERENCES prediction_sessions (uid)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prediction_uid ON detection_objects (prediction_uid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_label ON detection_objects (label)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON detection_objects (score)")

    async def save_prediction(self, uid, original_image, predicted_image):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO prediction_sessions (uid, original_image, predicted_image)
                VALUES (?, ?, ?)
            """, (uid, original_image, predicted_image))

    async def save_detection(self, prediction_uid, label, score, box):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)
            """, (prediction_uid, label, score, box))

    async def get_prediction(self, uid):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            session = conn.execute(
                "SELECT * FROM prediction_sessions WHERE uid = ?", (uid,)
            ).fetchone()
            if not session:
                return None
            objects = conn.execute(
                "SELECT * FROM detection_objects WHERE prediction_uid = ?", (uid,)
            ).fetchall()
            return {
                "uid": session["uid"],
                "timestamp": session["timestamp"],
                "original_image": session["original_image"],
                "predicted_image": session["predicted_image"],
                "detection_objects": [
                    {"id": o["id"], "label": o["label"], "score": o["score"], "box": o["box"]}
                    for o in objects
                ]
            }

    async def get_predictions_by_label(self, label):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT DISTINCT ps.uid, ps.timestamp
                  FROM prediction_sessions ps
                  JOIN detection_objects do ON ps.uid = do.prediction_uid
                 WHERE do.label = ?
            """, (label,)).fetchall()
            return [{"uid": r["uid"], "timestamp": r["timestamp"]} for r in rows]

    async def get_predictions_by_score(self, min_score):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT DISTINCT ps.uid, ps.timestamp
                  FROM prediction_sessions ps
                  JOIN detection_objects do ON ps.uid = do.prediction_uid
                 WHERE do.score >= ?
            """, (min_score,)).fetchall()
            return [{"uid": r["uid"], "timestamp": r["timestamp"]} for r in rows]

    async def get_prediction_image_path(self, uid):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT predicted_image FROM prediction_sessions WHERE uid = ?", (uid,)
            ).fetchone()
            return row[0] if row else None
