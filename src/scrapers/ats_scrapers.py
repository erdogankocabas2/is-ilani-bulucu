from typing import Any, Dict, List
from src.scrapers.base import BaseScraper
from src.utils.logger import logger

class ATSScraper(BaseScraper):
    def __init__(self):
        super().__init__("ATS Platforms (Greenhouse & Lever)")

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        ats_config = search_criteria.get("ats_platforms", {})
        greenhouse_slugs = ats_config.get("greenhouse_companies", [
            "gitlab", "canonical", "automattic", "elastic", "reddit", "airbnb", "stripe"
        ])
        lever_slugs = ats_config.get("lever_companies", [
            "spotify", "palantir", "figma", "atlassian"
        ])

        # 1. Greenhouse API
        for slug in greenhouse_slugs:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                res = self.session.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("jobs", [])
                    for item in items:
                        title = item.get("title", "")
                        location = item.get("location", {}).get("name", "Remote")
                        job_url = item.get("absolute_url", "")
                        content = item.get("content", "")

                        job = {
                            "title": title,
                            "company": slug.capitalize(),
                            "location": location,
                            "work_type": "remote" if "remote" in location.lower() else "hybrid",
                            "url": job_url,
                            "source": f"Greenhouse ({slug})",
                            "description": content,
                            "salary": "",
                            "posted_at": item.get("updated_at", ""),
                        }

                        if self.filter_job_by_criteria(job, search_criteria):
                            jobs.append(job)
            except Exception as e:
                logger.debug(f"Greenhouse ({slug}) çekerken hata: {e}")

        # 2. Lever API
        for slug in lever_slugs:
            try:
                url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                res = self.session.get(url, timeout=10)
                if res.status_code == 200:
                    items = res.json()
                    for item in items:
                        title = item.get("text", "")
                        categories = item.get("categories", {})
                        location = categories.get("location", "Remote")
                        commitment = categories.get("commitment", "")
                        job_url = item.get("hostedUrl", "")
                        desc = item.get("descriptionPlain", "")

                        job = {
                            "title": title,
                            "company": slug.capitalize(),
                            "location": location,
                            "work_type": "remote" if "remote" in location.lower() or "remote" in commitment.lower() else "hybrid",
                            "url": job_url,
                            "source": f"Lever ({slug})",
                            "description": desc,
                            "salary": "",
                            "posted_at": str(item.get("createdAt", "")),
                        }

                        if self.filter_job_by_criteria(job, search_criteria):
                            jobs.append(job)
            except Exception as e:
                logger.debug(f"Lever ({slug}) çekerken hata: {e}")

        logger.info(f"🏢 ATS Kaynakları (Greenhouse & Lever): {len(jobs)} uygun ilan bulundu.")
        return jobs
