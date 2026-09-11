import urllib.parse
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper
from src.utils.logger import logger

class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__("LinkedIn")
        self.base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        # Sadece Growth & Büyüme odaklı Türkiye aramaları
        growth_queries = [
            "Growth",
            "Growth Specialist",
            "Growth Marketing",
            "Growth Analyst",
            "Product Growth",
            "Junior Growth",
            "Growth Manager",
            "Performance Marketing",
            "User Acquisition"
        ]
        locations = ["Istanbul, Turkey", "Turkey"]

        for query in growth_queries:
            for loc in locations:
                params = {
                    "keywords": query,
                    "location": loc,
                    "f_E": "1,2,3", # Internship, Entry Level, Associate
                    "start": 0
                }
                try:
                    res = self.session.get(self.base_url, params=params, timeout=15)
                    if res.status_code != 200:
                        continue

                    soup = BeautifulSoup(res.text, "html.parser")
                    job_cards = soup.find_all("li")

                    for card in job_cards:
                        title_tag = card.find("h3", class_="base-search-card__title")
                        company_tag = card.find("h4", class_="base-search-card__subtitle")
                        location_tag = card.find("span", class_="job-search-card__location")
                        link_tag = card.find("a", class_="base-card__full-link")
                        time_tag = card.find("time")

                        if not title_tag or not link_tag:
                            continue

                        job_title = title_tag.get_text(strip=True)
                        company = company_tag.get_text(strip=True) if company_tag else "LinkedIn Şirketi"
                        location = location_tag.get_text(strip=True) if location_tag else loc
                        link = link_tag.get("href", "").split("?")[0]
                        posted_at = time_tag.get_text(strip=True) if time_tag else ""

                        job = {
                            "title": job_title,
                            "company": company,
                            "location": location,
                            "work_type": "remote" if "remote" in location.lower() or "uzaktan" in location.lower() else "hybrid",
                            "url": link,
                            "source": "LinkedIn (TR)",
                            "description": f"{company} şirketi {location} lokasyonunda {job_title} pozisyonu için ilan açtı.",
                            "salary": "",
                            "posted_at": posted_at,
                        }

                        if self.filter_job_by_criteria(job, search_criteria):
                            jobs.append(job)

                except Exception as e:
                    logger.debug(f"LinkedIn ({query} - {loc}) taranırken hata: {e}")

        logger.info(f"💼 LinkedIn (Sadece Growth): {len(jobs)} uygun ilan bulundu.")
        return jobs

class KariyerNetScraper(BaseScraper):
    def __init__(self):
        super().__init__("Kariyer.net")
        self.search_url = "https://www.kariyer.net/is-ilanlari"

    def fetch_jobs(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        growth_queries = [
            "growth",
            "growth specialist",
            "growth marketing",
            "büyüme uzmanı",
            "performance marketing",
            "user acquisition"
        ]

        for q in growth_queries:
            encoded_kw = urllib.parse.quote(q)
            url = f"{self.search_url}?kw={encoded_kw}"
            try:
                res = self.session.get(url, timeout=15)
                if res.status_code != 200:
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_="list-items") or soup.find_all("div", class_="k-ad-card")

                for card in cards:
                    title_elem = card.find("a", class_="k-ad-card-title") or card.find("span", class_="k-ad-card-title")
                    company_elem = card.find("a", class_="k-ad-card-subtitle") or card.find("span", class_="k-ad-card-subtitle")
                    link_elem = card.find("a", href=True)

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "Kariyer.net İlanı"
                    href = link_elem.get("href", "")
                    link = f"https://www.kariyer.net{href}" if href.startswith("/") else href

                    job = {
                        "title": title,
                        "company": company,
                        "location": "Türkiye / İstanbul",
                        "work_type": "hybrid",
                        "url": link,
                        "source": "Kariyer.net",
                        "description": f"{company} tarafından Kariyer.net üzerinde yayınlanan {title} ilanı.",
                        "salary": "",
                        "posted_at": "",
                    }

                    if self.filter_job_by_criteria(job, search_criteria):
                        jobs.append(job)

            except Exception as e:
                logger.debug(f"Kariyer.net ({q}) taranırken hata: {e}")

        logger.info(f"💼 Kariyer.net (Sadece Growth): {len(jobs)} uygun ilan bulundu.")
        return jobs
