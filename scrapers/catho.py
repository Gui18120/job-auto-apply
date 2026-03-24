"""
Scraper para vagas no Catho via scraping HTML.
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

    for keyword in keywords[:6]:
        try:
            url = f"https://www.catho.com.br/vagas/?q={requests.utils.quote(keyword)}&ordenar=recentes"
            resp = requests.get(url, headers=headers, timeout=(5, 15))
            if resp.status_code != 200:
                print(f"[Catho] Status {resp.status_code} para '{keyword}'")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select("article, div[class*='job-card'], li[class*='job']")
            if not cards:
                # fallback: tenta qualquer link de vaga
                cards = soup.select("a[href*='/vagas/']")

            for card in cards:
                link = card if card.name == "a" else card.select_one("a[href*='/vagas/']")
                if not link:
                    continue

                href = link.get("href", "")
                if not href or href == "/vagas/":
                    continue

                job_url = href if href.startswith("http") else f"https://www.catho.com.br{href}"
                job_id = f"catho_{abs(hash(job_url))}"

                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = card.select_one("h2, h3, [class*='title']")
                company = card.select_one("[class*='company'], [class*='empresa']")
                location = card.select_one("[class*='location'], [class*='cidade']")

                jobs.append({
                    "id": job_id,
                    "title": title.text.strip() if title else keyword,
                    "company": company.text.strip() if company else "",
                    "location": location.text.strip() if location else "Brasil",
                    "mode": "remote" if "remoto" in (location.text if location else "").lower() else "on-site",
                    "url": job_url,
                    "platform": "catho",
                    "description": "",
                })

            time.sleep(2)

        except Exception as e:
            print(f"[Catho] Erro ao buscar '{keyword}': {e}")

    print(f"[Catho] {len(jobs)} vagas encontradas")
    return jobs
