from typing import Any, Dict, List
import feedparser
from src.scrapers.base import BaseScraper
from src.utils.logger import logger

class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__("RemoteOK")
        self.api_url = "https://remoteok.com/api"

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        try:
            res = self.session.get(self.api_url, timeout=15)
            if res.status_code != 200:
                logger.warning(f"RemoteOK API yanıt vermedi (Status: {res.status_code})")
                return jobs

            data = res.json()
            # İlk eleman genellikle yasal bildirim / metadata objesidir
            items = data[1:] if len(data) > 1 and isinstance(data[0], dict) and "legal" in data[0] else data

            for item in items:
                if not isinstance(item, dict):
                    continue

                title = item.get("position", "")
                company = item.get("company", "")
                url = item.get("url", "")
                desc = item.get("description", "")
                location = item.get("location") or "Worldwide / Remote"
                salary = item.get("salary") or ""
                posted_at = item.get("date", "")

                job = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "work_type": "remote",
                    "url": url,
                    "source": "RemoteOK",
                    "description": desc,
                    "salary": salary,
                    "posted_at": posted_at,
                }

                if self.filter_job_by_criteria(job, search_criteria):
                    jobs.append(job)

            logger.info(f"🌐 RemoteOK: {len(jobs)} uygun ilan bulundu.")
        except Exception as e:
            logger.error(f"RemoteOK çekilirken hata: {e}")

        return jobs

class WeWorkRemotelyScraper(BaseScraper):
    def __init__(self):
        super().__init__("WeWorkRemotely")
        self.feeds = [
            "https://weworkremotely.com/categories/remote-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-product-management-jobs.rss",
            "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
            "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        ]

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        try:
            for feed_url in self.feeds:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries:
                    title_parts = entry.title.split(":") if ":" in entry.title else ["", entry.title]
                    company = title_parts[0].strip() if len(title_parts) > 1 else ""
                    title = title_parts[1].strip() if len(title_parts) > 1 else entry.title.strip()

                    job = {
                        "title": title,
                        "company": company or "WeWorkRemotely Company",
                        "location": "Remote",
                        "work_type": "remote",
                        "url": entry.link,
                        "source": "WeWorkRemotely",
                        "description": entry.summary,
                        "salary": "",
                        "posted_at": getattr(entry, "published", ""),
                    }

                    if self.filter_job_by_criteria(job, search_criteria):
                        jobs.append(job)

            logger.info(f"🌐 WeWorkRemotely: {len(jobs)} uygun ilan bulundu.")
        except Exception as e:
            logger.error(f"WeWorkRemotely çekilirken hata: {e}")

        return jobs

class JobicyScraper(BaseScraper):
    def __init__(self):
        super().__init__("Jobicy")
        self.api_url = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        try:
            res = self.session.get(self.api_url, params={"count": 50}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                items = data.get("jobs", [])
                for item in items:
                    job = {
                        "title": item.get("jobTitle", ""),
                        "company": item.get("companyName", ""),
                        "location": item.get("jobGeo", "Remote"),
                        "work_type": "remote",
                        "url": item.get("url", ""),
                        "source": "Jobicy",
                        "description": item.get("jobDescription", ""),
                        "salary": item.get("annualSalaryMin", "") or "",
                        "posted_at": item.get("pubDate", ""),
                    }

                    if self.filter_job_by_criteria(job, search_criteria):
                        jobs.append(job)

            logger.info(f"🌐 Jobicy: {len(jobs)} uygun ilan bulundu.")
        except Exception as e:
            logger.error(f"Jobicy çekilirken hata: {e}")

        return jobs
