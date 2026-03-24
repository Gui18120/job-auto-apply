"""
Scraper para Gupy via API pública.
Gupy é usado por centenas de empresas no Brasil como portal de vagas.
"""
import requests
import yaml
import os
from datetime import datetime, timedelta, timezone

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

    cutoff = datetime.now(timezone.utc) - timedelta(days=60)

    for keyword in keywords:
        print(f"[Gupy] Buscando: '{keyword}'...")
        params = {
            "jobName": keyword,
            "publishedDateOrder": "desc",
            "limit": 20,
            "offset": 0,
        }

        try:
            resp = requests.get(
                "https://portal.api.gupy.io/api/v1/jobs",
                params=params,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=(5, 10),
            )
            if resp.status_code != 200:
                print(f"[Gupy] Status {resp.status_code} para '{keyword}'")
                continue

            data = resp.json()
            for job in data.get("data", []):
                job_id = f"gupy_{job['id']}"
                if job_id in seen_ids:
                    continue

                # Filtra vagas antigas (mais de 60 dias)
                published = job.get("publishedDate") or job.get("applicationDeadline")
                if published:
                    try:
                        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        if pub_date < cutoff:
                            continue
                    except Exception:
                        pass

                seen_ids.add(job_id)

                workplace = job.get("workplaceType", "")
                mode_map = {"remote": "remote", "on-site": "on-site", "hybrid": "hybrid"}

                jobs.append({
                    "id": job_id,
                    "title": job.get("name", ""),
                    "company": job.get("company", {}).get("name", ""),
                    "location": f"{job.get('city', '')}, {job.get('state', '')}".strip(", "),
                    "mode": mode_map.get(workplace, workplace),
                    "url": job.get("jobUrl", ""),
                    "platform": "gupy",
                    "description": job.get("description", ""),
                })

        except Exception as e:
            print(f"[Gupy] Erro ao buscar '{keyword}': {e}")

    print(f"[Gupy] {len(jobs)} vagas encontradas")
    return jobs
