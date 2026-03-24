"""
Scraper para vagas no LinkedIn (sem login, via URL pública).
Retorna vagas com Easy Apply disponível.
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
        )
    }

    # Modos de trabalho LinkedIn: 1=presencial, 2=remoto, 3=híbrido
    work_types = ["1", "2", "3"]

    for keyword in keywords[:4]:  # limita para não ser bloqueado
        for city in cities:
            for wt in work_types:
                url = (
                    "https://www.linkedin.com/jobs/search/"
                    f"?keywords={requests.utils.quote(keyword)}"
                    f"&location={requests.utils.quote(city + ', Brazil')}"
                    f"&f_WT={wt}"
                    "&f_EA=true"   # Easy Apply apenas
                    "&sortBy=DD"   # mais recentes
                )
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.select("div.base-card")

                    for card in cards:
                        link_tag = card.select_one("a.base-card__full-link")
                        title_tag = card.select_one("h3.base-search-card__title")
                        company_tag = card.select_one("h4.base-search-card__subtitle")
                        location_tag = card.select_one("span.job-search-card__location")

                        if not link_tag:
                            continue

                        job_url = link_tag.get("href", "").split("?")[0]
                        job_id = f"linkedin_{job_url.split('/')[-1]}"

                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        mode_map = {"1": "on-site", "2": "remote", "3": "hybrid"}

                        jobs.append({
                            "id": job_id,
                            "title": title_tag.text.strip() if title_tag else "",
                            "company": company_tag.text.strip() if company_tag else "",
                            "location": location_tag.text.strip() if location_tag else city,
                            "mode": mode_map.get(wt, ""),
                            "url": job_url,
                            "platform": "linkedin",
                            "description": "",
                        })

                    time.sleep(1.5)  # evita bloqueio

                except Exception as e:
                    print(f"[LinkedIn] Erro ao buscar '{keyword}' em '{city}': {e}")

    print(f"[LinkedIn] {len(jobs)} vagas encontradas")
    return jobs
