"""
Scraper para vagas no Catho via API interna.
"""
import requests
import yaml
import os
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# IDs de estado no Catho (BA = 5)
CATHO_STATE_MAP = {
    "BA": 5,
    "SP": 27,
    "RJ": 21,
}


def search_jobs() -> list[dict]:
    config = load_config()
    keywords = config["search"]["keywords"]
    state_code = config["search"]["location"].get("states", ["BA"])[0]
    state_id = CATHO_STATE_MAP.get(state_code, 5)
    jobs = []
    seen_ids = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
        "Accept": "application/json",
        "Referer": "https://www.catho.com.br/",
    }

    for keyword in keywords[:5]:
        try:
            params = {
                "q": keyword,
                "state_id": state_id,
                "sort": "date",
                "page": 1,
                "limit": 20,
            }
            resp = requests.get(
                "https://www.catho.com.br/api/v2/jobs/search",
                params=params,
                headers=headers,
                timeout=15,
            )

            if resp.status_code != 200:
                print(f"[Catho] Status {resp.status_code} para '{keyword}'")
                continue

            data = resp.json()
            for job in data.get("data", {}).get("jobs", []):
                job_id = f"catho_{job.get('id', '')}"
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                jobs.append({
                    "id": job_id,
                    "title": job.get("title", ""),
                    "company": job.get("company", {}).get("name", "Confidencial"),
                    "location": job.get("city", "") + ", " + state_code,
                    "mode": job.get("workplace_type", ""),
                    "url": f"https://www.catho.com.br/vagas/{job.get('slug', '')}",
                    "platform": "catho",
                    "description": job.get("description", ""),
                })

            time.sleep(1.5)

        except Exception as e:
            print(f"[Catho] Erro ao buscar '{keyword}': {e}")

    print(f"[Catho] {len(jobs)} vagas encontradas")
    return jobs
