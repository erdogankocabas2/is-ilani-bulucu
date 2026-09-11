import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.utils.logger import logger

DB_PATH = Path("data/jobs.db")

class JobDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Veritabanı tablolarını ve indeksleri oluşturur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    work_type TEXT,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT,
                    salary TEXT,
                    posted_at TEXT,
                    ai_score INTEGER DEFAULT 0,
                    ai_summary TEXT,
                    key_skills TEXT,
                    pros_cons TEXT,
                    is_sent INTEGER DEFAULT 0,
                    synced_to_sheets INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_hash ON jobs(job_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_sent ON jobs(is_sent);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_synced_to_sheets ON jobs(synced_to_sheets);")
            conn.commit()

    @staticmethod
    def generate_hash(title: str, company: str, url: str) -> str:
        """İlan için tekil bir MD5 hash üretir."""
        raw = f"{company.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def is_job_seen(self, job_hash: str) -> bool:
        """Bu ilan daha önce kaydedilmiş mi kontrol eder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE job_hash = ?", (job_hash,))
            return cursor.fetchone() is not None

    def insert_job(self, job_data: Dict[str, Any]) -> Optional[int]:
        """Yeni bir ilanı veritabanına ekler (Zaten varsa eklemez)."""
        job_hash = job_data.get("job_hash") or self.generate_hash(
            job_data.get("title", ""),
            job_data.get("company", ""),
            job_data.get("url", "")
        )
        job_data["job_hash"] = job_hash

        if self.is_job_seen(job_hash):
            return None

        key_skills = job_data.get("key_skills", [])
        if isinstance(key_skills, list):
            key_skills = json.dumps(key_skills, ensure_ascii=False)

        pros_cons = job_data.get("pros_cons", {})
        if isinstance(pros_cons, dict):
            pros_cons = json.dumps(pros_cons, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO jobs (
                        job_hash, title, company, location, work_type, url,
                        source, description, salary, posted_at, ai_score,
                        ai_summary, key_skills, pros_cons, is_sent, synced_to_sheets
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_hash,
                    job_data.get("title", ""),
                    job_data.get("company", ""),
                    job_data.get("location", ""),
                    job_data.get("work_type", "remote"),
                    job_data.get("url", ""),
                    job_data.get("source", "unknown"),
                    job_data.get("description", ""),
                    job_data.get("salary", ""),
                    job_data.get("posted_at", ""),
                    job_data.get("ai_score", 0),
                    job_data.get("ai_summary", ""),
                    key_skills,
                    pros_cons,
                    0,
                    0
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

    def update_job_ai_analysis(self, job_id: int, ai_score: int, ai_summary: str, key_skills: List[str], pros_cons: Dict[str, Any]):
        """Gemini AI analiz sonuçlarını günceller."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET ai_score = ?,
                    ai_summary = ?,
                    key_skills = ?,
                    pros_cons = ?
                WHERE id = ?
            """, (
                ai_score,
                ai_summary,
                json.dumps(key_skills, ensure_ascii=False),
                json.dumps(pros_cons, ensure_ascii=False),
                job_id
            ))
            conn.commit()

    def get_unsent_jobs(self, min_score: int = 0) -> List[Dict[str, Any]]:
        """E-posta ile gönderilmemiş ve puan eşiğini aşan ilanları döndürür."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM jobs
                WHERE is_sent = 0 AND ai_score >= ?
                ORDER BY ai_score DESC, id DESC
            """, (min_score,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_jobs_as_sent(self, job_ids: List[int]):
        """İlanları e-posta gönderildi olarak işaretler."""
        if not job_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(job_ids))
            cursor.execute(f"UPDATE jobs SET is_sent = 1 WHERE id IN ({placeholders})", job_ids)
            conn.commit()

    def get_unsynced_to_sheets_jobs(self) -> List[Dict[str, Any]]:
        """Google Sheets'e henüz yazılmamış ilanları getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM jobs
                WHERE synced_to_sheets = 0
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_jobs_as_synced_to_sheets(self, job_ids: List[int]):
        """İlanları Google Sheets senkronize edildi olarak işaretler."""
        if not job_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(job_ids))
            cursor.execute(f"UPDATE jobs SET synced_to_sheets = 1 WHERE id IN ({placeholders})", job_ids)
            conn.commit()

    def get_total_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            return cursor.fetchone()[0]

db = JobDatabase()
