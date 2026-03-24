"""
Scraper para Gupy via API pública.
Gupy é usado por centenas de empresas no Brasil como portal de vagas.
"""
import requests
import yaml
import os

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

    for keyword in keywords:
        for city in cities + [None]:  # busca com e sem filtro de cidade
            params = {
                "jobName": keyword,
                "publishedDateOrder": "desc",
                "limit": 20,
                "offset": 0,
            }
            if city:
                params["city"] = city

            try:
                resp = requests.get(
                    "https://portal.api.gupy.io/api/v1/jobs",
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if resp.status_code != 200:
                    print(f"[Gupy] Status {resp.status_code} para '{keyword}'")
                    continue

                data = resp.json()
                for job in data.get("data", []):
                    job_id = f"gupy_{job['id']}"
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    workplace = job.get("workplaceType", "")
                    mode_map = {
                        "remote": "remote",
                        "on-site": "on-site",
                        "hybrid": "hybrid",
                    }

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
                print(f"[Gupy] Erro ao buscar '{keyword}' em '{city}': {e}")

    print(f"[Gupy] {len(jobs)} vagas encontradas")
    return jobs
