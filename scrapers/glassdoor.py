"""
Scraper para vagas no Glassdoor via scraping público.
"""
import requests
from bs4 import BeautifulSoup
import yaml
import os
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def search_jobs() -> list[dict]:
    config = load_config()
    keywords = config["search"]["keywords"]
    jobs = []
    seen_ids = set()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    search_locations = ["Salvador, Bahia, Brasil", "Brasil", "Remote"]

    for keyword in keywords[:5]:
        for location in search_locations:
            url = (
                "https://www.glassdoor.com.br/Vagas/index.htm"
                f"?sc.keyword={requests.utils.quote(keyword)}"
                f"&locT=C&locKeyword={requests.utils.quote(location)}"
                "&sortBy=date_desc"
            )
            try:
                resp = requests.get(url, headers=headers, timeout=(5, 15))
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("li.react-job-listing, div[data-test='jobListing']")

                for card in cards:
                    link = card.select_one("a[data-test='job-link'], a.jobLink")
                    title = card.select_one("[data-test='job-title'], .job-title")
                    company = card.select_one("[data-test='employer-name'], .employer-name")
                    loc = card.select_one("[data-test='emp-location'], .location")

                    if not link:
                        continue

                    job_url = "https://www.glassdoor.com.br" + link.get("href", "")
                    job_id = f"glassdoor_{abs(hash(job_url))}"

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    mode = "remote" if "remote" in location.lower() or "remoto" in (loc.text if loc else "").lower() else "on-site"

                    jobs.append({
                        "id": job_id,
                        "title": title.text.strip() if title else "",
                        "company": company.text.strip() if company else "",
                        "location": loc.text.strip() if loc else location,
                        "mode": mode,
                        "url": job_url,
                        "platform": "glassdoor",
                        "description": "",
                    })

                time.sleep(2)

            except Exception as e:
                print(f"[Glassdoor] Erro ao buscar '{keyword}' em '{location}': {e}")

    print(f"[Glassdoor] {len(jobs)} vagas encontradas")
    return jobs
