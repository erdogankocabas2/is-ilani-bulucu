from abc import ABC, abstractmethod
from typing import Any, Dict, List
import requests
from src.utils.logger import logger

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        })

    @abstractmethod
    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Her platform için ilanları çeken ana metot.
        Döndürülmesi gereken standart sözlük formatı:
        {
            "title": str,
            "company": str,
            "location": str,
            "work_type": "remote" | "hybrid" | "onsite",
            "url": str,
            "source": str,
            "description": str,
            "salary": str,
            "posted_at": str,
        }
        """
        pass

    def filter_job_by_criteria(self, job: Dict[str, Any], search_criteria: Dict[str, Any]) -> bool:
        """İlanın verilen anahtar kelimelere ve negatif filtrelere uyup uymadığını kontrol eder."""
        title = job.get("title", "").lower()
        desc = job.get("description", "").lower()
        full_text = f"{title} {desc}"

        # 1. KESİN ELEME: Senior, Lead, Yönetici, vb.
        strict_senior_patterns = [
            "senior", "sr.", "sr ", "lead", "principal", "staff", "director",
            "head of", "vice president", "vp ", "vp,", "chief", "architect",
            "5+ years", "5+ yıl", "7+ years", "10+ years", "8+ years"
        ]
        for pattern in strict_senior_patterns:
            # Başlıkta doğrudan geçiyorsa kesinlikle ele
            if pattern in title:
                return False

        # Negatif kelimeler (config'den gelen)
        negatives = search_criteria.get("negative_keywords", [])
        for neg in negatives:
            if neg.lower() in full_text:
                return False

        # 2. Başlık ve anahtar kelimeler
        job_titles = search_criteria.get("job_titles", [])
        keywords = search_criteria.get("keywords", [])

        title_match = any(t.lower() in title for t in job_titles) if job_titles else True
        keyword_match = any(k.lower() in full_text for k in keywords) if keywords else True

        return title_match or keyword_match
