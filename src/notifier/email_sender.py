import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List
from jinja2 import Environment, FileSystemLoader
from src.utils.config_loader import config
from src.utils.logger import logger

TEMPLATES_DIR = Path(__file__).parent / "templates"

class EmailSender:
    def __init__(self):
        self.enabled = config.get("email.enabled", True)
        self.smtp_host = config.get("email.smtp_host", "smtp.gmail.com")
        self.smtp_port = int(config.get("email.smtp_port", 587))
        self.use_tls = config.get("email.use_tls", True)
        self.sender_email = config.get("email.sender_email", "")
        self.sender_password = config.get("email.smtp_password", "")
        self.sender_name = config.get("email.sender_name", "Job Radar AI")
        self.recipient_email = config.get("email.recipient_email", "")
        self.subject_prefix = config.get("email.subject_prefix", "🎯 Günlük İş İlanı Bülteni")
        
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        self.template = self.env.get_template("email_digest.html")

    def send_job_digest(self, jobs: List[Dict[str, Any]]) -> bool:
        """İlan listesini şık bir HTML bülteni olarak e-posta ile gönderir."""
        if not self.enabled:
            logger.info("ℹ️ E-posta gönderimi config üzerinden devre dışı bırakılmış.")
            return False

        if not jobs:
            logger.info("ℹ️ Gönderilecek yeni ilan bulunmuyor.")
            return False

        if not self.sender_email or not self.recipient_email or not self.sender_password:
            logger.warning(
                "⚠️ E-posta bilgileri (SENDER_EMAIL / SMTP_PASSWORD / RECIPIENT_EMAIL) eksik. "
                "E-posta gönderimi atlandı. Lütfen .env veya config.yaml dosyasını doldurun."
            )
            return False

        # İlan verilerini şablon için hazırlayalım (JSON string olanları listeye çevir)
        formatted_jobs = []
        for j in jobs:
            item = dict(j)
            skills = item.get("key_skills", [])
            if isinstance(skills, str):
                try:
                    item["key_skills_list"] = json.loads(skills)
                except Exception:
                    item["key_skills_list"] = [skills]
            else:
                item["key_skills_list"] = skills
            formatted_jobs.append(item)

        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        subject = f"🚀 Growth & Büyüme Fırsatları Bülteni - {len(jobs)} Yeni İlan ({datetime.now().strftime('%d.%m.%Y')})"

        html_content = self.template.render(
            subject=subject,
            jobs=formatted_jobs,
            date_str=date_str
        )

        plain_text = f"🚀 Job Radar AI - Yeni Mezun & Junior Growth İlanları ({len(jobs)} İlan)\n\n"
        for idx, job in enumerate(jobs, 1):
            plain_text += f"{idx}. [ŞİRKET: {job.get('company')}] - {job.get('title')}\nUyum Skoru: %{job.get('ai_score', 0)}\nLokasyon: {job.get('location')}\nBaşvuru Linki: {job.get('url')}\n\n"

        # E-posta mesajı oluştur
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = self.recipient_email

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            logger.info(f"📧 E-posta gönderiliyor: {self.recipient_email} ({self.smtp_host}:{self.smtp_port})...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            logger.info(f"✅ E-posta başarıyla gönderildi: [bold green]{self.recipient_email}[/bold green]")
            return True
        except Exception as e:
            logger.error(f"E-posta gönderimi başarısız: {e}")
            return False

email_sender = EmailSender()
