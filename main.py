import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.utils.logger import logger, console
from src.utils.config_loader import config
from src.storage.db import db
from src.ai.resume_parser import resume_parser
from src.ai.analyzer import analyzer
from src.storage.sheets_sync import sheets_sync
from src.notifier.email_sender import email_sender

# Scrapers
from src.scrapers.remote_portals import RemoteOKScraper, WeWorkRemotelyScraper, JobicyScraper
from src.scrapers.job_boards import LinkedInScraper, KariyerNetScraper
from src.scrapers.ats_scrapers import ATSScraper

def get_active_scrapers() -> list:
    """Config'e göre aktif olan tüm scraper'ları döndürür."""
    scrapers = []
    
    # Remote Portalleri
    if config.get("sources.remote_portals.enabled", True):
        if config.get("sources.remote_portals.remoteok", True):
            scrapers.append(RemoteOKScraper())
        if config.get("sources.remote_portals.weworkremotely", True):
            scrapers.append(WeWorkRemotelyScraper())
        if config.get("sources.remote_portals.jobicy", True):
            scrapers.append(JobicyScraper())

    # Job Boards
    if config.get("sources.job_boards.enabled", True):
        if config.get("sources.job_boards.linkedin", True):
            scrapers.append(LinkedInScraper())
        if config.get("sources.job_boards.kariyer_net", True):
            scrapers.append(KariyerNetScraper())

    # ATS
    if config.get("sources.ats_platforms.enabled", True):
        scrapers.append(ATSScraper())

    return scrapers

def run_scrapers() -> List[Dict[str, Any]]:
    """Tüm aktif kaynaklardan ilanları toplar."""
    active_scrapers = get_active_scrapers()
    search_criteria = config.get("search_criteria", {})
    all_raw_jobs = []

    console.print(Panel.fit(
        f"[bold blue]🚀 İş İlanı Tarama Başlatılıyor[/bold blue]\n"
        f"Aktif Kaynak Sayısı: [bold green]{len(active_scrapers)}[/bold green]\n"
        f"Tarih: [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/cyan]",
        border_style="blue"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        for scraper in active_scrapers:
            task = progress.add_task(description=f"{scraper.name} taranıyor...", total=None)
            try:
                jobs = scraper.fetch_jobs(search_criteria)
                all_raw_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"{scraper.name} çalıştırılırken beklenmeyen hata: {e}")
            finally:
                progress.remove_task(task)

    logger.info(f"📊 Toplam taranan ham ilan sayısı: [bold cyan]{len(all_raw_jobs)}[/bold cyan]")
    return all_raw_jobs

def run_pipeline():
    """Uçtan uca tam iş akışını çalıştırır."""
    # 1. Scrape
    raw_jobs = run_scrapers()
    if not raw_jobs:
        logger.info("Tarama sonucunda yeni ilan bulunamadı.")
        return

    # 2. Veritabanına Ekleme & Tekilleştirme
    new_jobs_saved = []
    for job in raw_jobs:
        job_id = db.insert_job(job)
        if job_id:
            job["id"] = job_id
            new_jobs_saved.append(job)

    logger.info(f"✨ Tekilleştirme sonrası yeni eklenen ilan sayısı: [bold green]{len(new_jobs_saved)}[/bold green]")
    if not new_jobs_saved:
        logger.info("Yeni ilan bulunmuyor, tüm ilanlar daha önce işlenmiş.")
        return

    # 3. AI Analiz ve Puanlama
    candidate_cv = resume_parser.get_profile_summary()
    logger.info("🤖 Gemini AI ile ilanlar analiz ediliyor...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        for idx, job in enumerate(new_jobs_saved, 1):
            task = progress.add_task(description=f"[{idx}/{len(new_jobs_saved)}] {job['title']} ({job['company']}) analiz ediliyor...", total=None)
            analysis = analyzer.analyze_job(job, candidate_cv)
            
            db.update_job_ai_analysis(
                job_id=job["id"],
                ai_score=analysis.get("ai_score", 50),
                ai_summary=analysis.get("ai_summary", ""),
                key_skills=analysis.get("key_skills", []),
                pros_cons=analysis.get("pros_cons", {})
            )
            job.update(analysis)
            progress.remove_task(task)

    # 4. Google Sheets / CSV Senkronizasyonu
    sheets_sync.sync_unsynced_jobs()

    # 5. E-posta Gönderimi (Eşik puanını aşanlar)
    min_score = config.get("profile.min_match_score", 65)
    unsent_jobs = db.get_unsent_jobs(min_score=min_score)

    if unsent_jobs:
        logger.info(f"📬 Eşik puanını (%{min_score}+) aşan {len(unsent_jobs)} ilan için e-posta hazırlanıyor...")
        
        # Konsolda şık özet tablosu gösterelim
        table = Table(title=f"🎯 E-posta Gönderilecek İlanlar (Min Skor: %{min_score})")
        table.add_column("Skor", style="cyan", justify="center")
        table.add_column("Pozisyon", style="bold white")
        table.add_column("Şirket", style="blue")
        table.add_column("Kaynak", style="magenta")
        table.add_column("Lokasyon", style="green")

        for j in unsent_jobs:
            score = j.get("ai_score", 0)
            score_color = "green" if score >= 80 else ("yellow" if score >= 65 else "red")
            table.add_row(
                f"[{score_color}]%{score}[/{score_color}]",
                j.get("title", ""),
                j.get("company", ""),
                j.get("source", ""),
                j.get("location", "")
            )
        console.print(table)

        success = email_sender.send_job_digest(unsent_jobs)
        if success:
            sent_ids = [j["id"] for j in unsent_jobs]
            db.mark_jobs_as_sent(sent_ids)
    else:
        logger.info(f"ℹ️ Bu taramada eşik puanını (%{min_score}) aşan yeni ilan bulunamadı.")

def test_email():
    """Örnek verilerle e-posta şablonunu ve SMTP gönderimini test eder."""
    logger.info("🧪 Test e-postası hazırlanıyor...")
    mock_jobs = [
        {
            "id": 9991,
            "title": "Senior AI Product Manager",
            "company": "TechVision AI",
            "location": "Remote / Worldwide",
            "work_type": "remote",
            "url": "https://example.com/job/1",
            "source": "RemoteOK",
            "salary": "$120,000 - $160,000",
            "ai_score": 92,
            "ai_summary": "Boğaziçi mezuniyeti, Getirfinans yapay zeka asistanı deneyimi ve ürün yönetimi geçmişinizle %92 oranında kusursuz eşleşiyor.",
            "key_skills_list": ["Product Strategy", "AI Assistants", "LLMs", "Python", "CX"]
        },
        {
            "id": 9992,
            "title": "Business Development & Growth Lead",
            "company": "NextGen Scale",
            "location": "Istanbul / Hybrid",
            "work_type": "hybrid",
            "url": "https://example.com/job/2",
            "source": "LinkedIn",
            "salary": "₺80,000 - ₺110,000",
            "ai_score": 85,
            "ai_summary": "P&G marka yönetimi ve Buluttan iş geliştirme deneyimleriniz bu roldeki büyüme ve hesap yönetimi hedefleriyle tam örtüşmektedir.",
            "key_skills_list": ["Business Development", "Growth Marketing", "B2B Sales", "Analytics"]
        }
    ]
    email_sender.send_job_digest(mock_jobs)

def test_ai():
    """Gemini AI ve CV parser modülünü örnek bir ilanla test eder."""
    logger.info("🧪 AI Analiz Motoru ve CV eşleştirme testi başlatılıyor...")
    cv_summary = resume_parser.get_profile_summary()
    console.print(Panel(cv_summary[:500] + "\n...", title="📄 Yüklenen CV Özeti", border_style="cyan"))

    mock_job = {
        "title": "Product Manager - AI & Customer Experience",
        "company": "Fintech Solutions Inc.",
        "location": "Remote",
        "work_type": "remote",
        "description": "We are seeking a Product Manager to lead the development of our customer-facing AI agents and voice-of-customer analytics tools. Requirements: Experience with AI/LLMs, Customer Journey mapping, cross-functional collaboration with engineering and growth teams. Python and SQL knowledge is a plus."
    }

    result = analyzer.analyze_job(mock_job, cv_summary)
    console.print(Panel.fit(
        f"[bold]Pozisyon:[/bold] {mock_job['title']}\n"
        f"[bold]Uyum Skoru:[/bold] [bold green]%{result.get('ai_score')}[/bold green]\n"
        f"[bold]AI Özeti:[/bold] {result.get('ai_summary')}\n"
        f"[bold]Anahtar Yetenekler:[/bold] {', '.join(result.get('key_skills', []))}\n"
        f"[bold]Eşleşme Nedenleri:[/bold] {result.get('pros_cons', {}).get('match_reasons', [])}",
        title="✨ Gemini Analiz Çıktısı",
        border_style="green"
    ))

def run_morning_scheduler(target_time: str = "09:00"):
    """Belirtilen saatte (varsayılan 09:00) her sabah otomatik çalışan Python zamanlayıcı."""
    import time
    logger.info(f"⏰ Sabah Otomasyonu başlatıldı! Sistem her sabah saat [bold green]{target_time}[/bold green]'da otomatik tarama yapacak.")
    logger.info("Durdurmak için Ctrl+C tuşlarına basabilirsiniz.")
    
    last_run_date = None

    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        current_date_str = now.strftime("%Y-%m-%d")

        if current_time_str == target_time and last_run_date != current_date_str:
            logger.info(f"🔔 Sabah saat {target_time} oldu! Otomatik tarama ve bülten gönderimi başlatılıyor...")
            try:
                run_pipeline()
                last_run_date = current_date_str
            except Exception as e:
                logger.error(f"Zamanlanmış görev çalıştırılırken hata: {e}")

        # Her 30 saniyede bir saati kontrol et
        time.sleep(30)

def main():
    parser = argparse.ArgumentParser(description="Job Radar AI - Otomatik İş İlanı Tarayıcı ve Raporlayıcı")
    parser.add_argument("--run-once", action="store_true", help="Tek seferlik tam iş akışını (Scrape -> DB -> AI -> Sheets -> Email) çalıştır")
    parser.add_argument("--test-email", action="store_true", help="Örnek ilanlarla test e-postası gönder")
    parser.add_argument("--test-scrapers", action="store_true", help="Sadece scraper'ları çalıştır ve sonuçları listele")
    parser.add_argument("--test-ai", action="store_true", help="Gemini AI ve CV eşleştirme analizini test et")
    parser.add_argument("--sync-sheets", action="store_true", help="Veritabanındaki yeni ilanları Google Sheets/CSV'ye aktar")
    parser.add_argument("--schedule", nargs="?", const="09:00", help="Belirtilen saatte her sabah arka planda çalışacak zamanlayıcıyı başlat (Örn: --schedule 09:00)")

    args = parser.parse_args()

    if args.test_email:
        test_email()
    elif args.test_ai:
        test_ai()
    elif args.test_scrapers:
        run_scrapers()
    elif args.sync_sheets:
        sheets_sync.sync_unsynced_jobs()
    elif args.schedule:
        run_morning_scheduler(args.schedule)
    else:
        # Varsayılan olarak tam pipeline çalıştır
        run_pipeline()

if __name__ == "__main__":
    main()

