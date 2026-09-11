import os
import tempfile
from pathlib import Path
import pytest
from src.storage.db import JobDatabase
from src.ai.resume_parser import ResumeParser
from src.ai.analyzer import JobAnalyzer
from src.scrapers.base import BaseScraper
from src.notifier.email_sender import EmailSender

class MockScraper(BaseScraper):
    def fetch_jobs(self, search_criteria):
        return []

def test_resume_parser_finds_pdf():
    parser = ResumeParser()
    summary = parser.get_profile_summary()
    assert len(summary) > 50
    assert "Erdoğan" in summary or "Boğaziçi" in summary or "Aday Profili" in summary

def test_sqlite_db_deduplication():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        test_db = JobDatabase(db_path=db_path)
        job_data = {
            "title": "Senior AI Product Manager",
            "company": "Test Company",
            "location": "Remote",
            "work_type": "remote",
            "url": "https://example.com/job/test1",
            "source": "RemoteOK",
            "description": "Test job description with Python and LLM",
        }

        # İlk ekleme
        job_id = test_db.insert_job(job_data)
        assert job_id is not None
        assert test_db.get_total_count() == 1

        # İkinci ekleme (Duplicate)
        duplicate_id = test_db.insert_job(job_data)
        assert duplicate_id is None
        assert test_db.get_total_count() == 1

        # AI Analiz güncelleme
        test_db.update_job_ai_analysis(
            job_id=job_id,
            ai_score=88,
            ai_summary="Harika bir uyum.",
            key_skills=["Python", "AI"],
            pros_cons={"match_reasons": ["Yetenekler uyuyor"]}
        )

        unsent = test_db.get_unsent_jobs(min_score=80)
        assert len(unsent) == 1
        assert unsent[0]["ai_score"] == 88

        # Gönderildi olarak işaretle
        test_db.mark_jobs_as_sent([job_id])
        unsent_after = test_db.get_unsent_jobs(min_score=80)
        assert len(unsent_after) == 0

    finally:
        if db_path.exists():
            db_path.unlink()

def test_scraper_filter_logic():
    scraper = MockScraper("TestMock")
    criteria = {
        "job_titles": ["Product Manager", "Software Engineer"],
        "keywords": ["Python", "AI"],
        "negative_keywords": ["Stajyer", "WordPress"]
    }

    # Uygun ilan
    valid_job = {
        "title": "AI Product Manager",
        "description": "We build Python LLM tools."
    }
    assert scraper.filter_job_by_criteria(valid_job, criteria) is True

    # Negatif kelime içeren ilan
    negative_job = {
        "title": "WordPress Developer",
        "description": "We need WordPress maintenance."
    }
    assert scraper.filter_job_by_criteria(negative_job, criteria) is False

def test_analyzer_fallback():
    analyzer = JobAnalyzer()
    analyzer.client = None # Force fallback

    job = {
        "title": "Product Manager - AI",
        "company": "Tech Corp",
        "description": "Looking for Python, LLM and Product management skills."
    }
    result = analyzer.analyze_job(job)
    assert "ai_score" in result
    assert result["ai_score"] > 0
    assert "ai_summary" in result

def test_email_template_rendering():
    sender = EmailSender()
    mock_jobs = [
        {
            "id": 1,
            "title": "AI Engineer",
            "company": "Google",
            "location": "Remote",
            "work_type": "remote",
            "url": "https://google.com/jobs/1",
            "source": "LinkedIn",
            "ai_score": 95,
            "ai_summary": "Kusursuz eşleşme.",
            "key_skills_list": ["Python", "Gemini", "PyTorch"]
        }
    ]
    html = sender.template.render(
        subject="Test Subject",
        jobs=mock_jobs,
        date_str="10.09.2026"
    )
    assert "AI Engineer" in html
    assert "Google" in html
    assert "%95" in html
    assert "https://google.com/jobs/1" in html
