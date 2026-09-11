import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List
from src.utils.config_loader import config
from src.utils.logger import logger
from src.storage.db import db

CSV_BACKUP_PATH = Path("data/jobs_export.csv")

class GoogleSheetsSync:
    def __init__(self):
        self.enabled = config.get("google_sheets.enabled", False)
        self.credentials_path = config.get("google_sheets.credentials_json", "credentials.json")
        self.spreadsheet_name = config.get("google_sheets.spreadsheet_name", "İş İlanları Takip Tablosu")
        self.worksheet_name = config.get("google_sheets.worksheet_name", "İlanlar")
        self.client = None
        self._init_client()

    def _init_client(self):
        """Google Service Account ile bağlantı kurar."""
        if not self.enabled:
            return

        if not Path(self.credentials_path).exists():
            logger.warning(
                f"Google Sheets aktif ancak kimlik dosyası bulunamadı: {self.credentials_path}. "
                "İlanlar CSV formatında (data/jobs_export.csv) yedeklenecektir."
            )
            return

        try:
            import gspread
            self.client = gspread.service_account(filename=self.credentials_path)
            logger.info("📊 Google Sheets bağlantısı başarılı.")
        except Exception as e:
            logger.error(f"Google Sheets bağlantısı kurulamadı: {e}")
            self.client = None

    def sync_unsynced_jobs(self) -> int:
        """Henüz senkronize edilmemiş ilanları Google Sheets'e veya CSV'ye yazar."""
        jobs = db.get_unsynced_to_sheets_jobs()
        if not jobs:
            return 0

        # Her zaman yerel CSV yedeğini de güncelleyelim
        self._export_to_csv(jobs)

        if self.client:
            try:
                self._sync_to_google_sheets(jobs)
            except Exception as e:
                logger.error(f"Google Sheets senkronizasyon hatası: {e}")
                return 0

        synced_ids = [j["id"] for j in jobs]
        db.mark_jobs_as_synced_to_sheets(synced_ids)
        logger.info(f"✅ {len(jobs)} ilan e-tabloya (Sheets/CSV) senkronize edildi.")
        return len(jobs)

    def _sync_to_google_sheets(self, jobs: List[Dict[str, Any]]):
        """Google E-Tablosuna satır ekler."""
        try:
            sh = self.client.open(self.spreadsheet_name)
        except Exception:
            sh = self.client.create(self.spreadsheet_name)

        try:
            ws = sh.worksheet(self.worksheet_name)
        except Exception:
            ws = sh.add_worksheet(title=self.worksheet_name, rows=1000, cols=12)
            headers = [
                "ID", "Tarih", "Uyum Skoru", "Pozisyon", "Şirket",
                "Lokasyon", "Kaynak", "Özet", "Yetenekler", "Başvuru Linki", "Durum"
            ]
            ws.append_row(headers)

        rows_to_add = []
        for j in jobs:
            skills = j.get("key_skills", "")
            if isinstance(skills, str) and skills.startswith("["):
                try:
                    skills = ", ".join(json.loads(skills))
                except Exception:
                    pass

            row = [
                j.get("id"),
                j.get("created_at"),
                j.get("ai_score"),
                j.get("title"),
                j.get("company"),
                j.get("location"),
                j.get("source"),
                j.get("ai_summary"),
                skills,
                j.get("url"),
                "İncelenecek"
            ]
            rows_to_add.append(row)

        if rows_to_add:
            ws.append_rows(rows_to_add)

    def _export_to_csv(self, jobs: List[Dict[str, Any]]):
        """Yerel CSV dosyasına satırları yazar."""
        CSV_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        file_exists = CSV_BACKUP_PATH.exists()

        with open(CSV_BACKUP_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "ID", "Tarih", "Uyum Skoru", "Pozisyon", "Şirket",
                    "Lokasyon", "Kaynak", "Özet", "Yetenekler", "Başvuru Linki", "Durum"
                ])
            for j in jobs:
                skills = j.get("key_skills", "")
                if isinstance(skills, str) and skills.startswith("["):
                    try:
                        skills = ", ".join(json.loads(skills))
                    except Exception:
                        pass
                writer.writerow([
                    j.get("id"),
                    j.get("created_at"),
                    j.get("ai_score"),
                    j.get("title"),
                    j.get("company"),
                    j.get("location"),
                    j.get("source"),
                    j.get("ai_summary"),
                    skills,
                    j.get("url"),
                    "İncelenecek"
                ])

sheets_sync = GoogleSheetsSync()
