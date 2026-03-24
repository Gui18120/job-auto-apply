"""
Scraper para vagas no Indeed Brasil.
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
    cities = config["search"]["location"].get("cities", [])
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

    for keyword in keywords[:5]:
        for city in cities:
            params = {
                "q": keyword,
                "l": city,
                "sort": "date",
                "fromage": "7",  # últimos 7 dias
            }
            try:
                resp = requests.get(
                    "https://br.indeed.com/jobs",
                    params=params,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    print(f"[Indeed] Status {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select("div.job_seen_beacon")

                for card in cards:
                    job_id_tag = card.get("data-jk") or card.select_one("[data-jk]")
                    title_tag = card.select_one("h2.jobTitle span[title]")
                    company_tag = card.select_one("span.companyName")
                    location_tag = card.select_one("div.companyLocation")

                    raw_id = (
                        card.get("data-jk")
                        or (job_id_tag.get("data-jk") if hasattr(job_id_tag, "get") else None)
                    )
                    if not raw_id:
                        continue

                    job_id = f"indeed_{raw_id}"
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    jobs.append({
                        "id": job_id,
                        "title": title_tag.get("title", "").strip() if title_tag else "",
                        "company": company_tag.text.strip() if company_tag else "",
                        "location": location_tag.text.strip() if location_tag else city,
                        "mode": "",
                        "url": f"https://br.indeed.com/viewjob?jk={raw_id}",
                        "platform": "indeed",
                        "description": "",
                    })

                time.sleep(2)

            except Exception as e:
                print(f"[Indeed] Erro ao buscar '{keyword}' em '{city}': {e}")

    print(f"[Indeed] {len(jobs)} vagas encontradas")
    return jobs
