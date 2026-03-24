"""
Scraper para vagas no Catho via Playwright.
"""
import yaml
import os
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def search_jobs() -> list[dict]:
    from playwright.sync_api import sync_playwright

    config = load_config()
    keywords = config["search"]["keywords"]
    jobs = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        for keyword in keywords[:6]:
            try:
                import requests as _r
                url = f"https://www.catho.com.br/vagas/?q={_r.utils.quote(keyword)}&ordenar=recentes"
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                time.sleep(3)

                links = page.locator("a[href*='/vagas/']").all()

                for link in links:
                    href = link.get_attribute("href") or ""
                    # só links de vaga específica (não listagem)
                    if not href or href.count("/") < 3 or href == "/vagas/":
                        continue

                    job_url = href if href.startswith("http") else f"https://www.catho.com.br{href}"
                    job_id = f"catho_{abs(hash(job_url))}"

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    title_text = link.inner_text().strip()
                    if not title_text or len(title_text) < 3:
                        continue

                    jobs.append({
                        "id": job_id,
                        "title": title_text,
                        "company": "",
                        "location": "Brasil",
                        "mode": "on-site",
                        "url": job_url,
                        "platform": "catho",
                        "description": "",
                    })

                time.sleep(2)

            except Exception as e:
                print(f"[Catho] Erro ao buscar '{keyword}': {e}")

        browser.close()

    print(f"[Catho] {len(jobs)} vagas encontradas")
    return jobs
