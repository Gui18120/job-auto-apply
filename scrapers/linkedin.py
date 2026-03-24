"""
Scraper para vagas no LinkedIn via Playwright (logado com cookies salvos).
Retorna apenas vagas com Easy Apply disponível.
"""
import yaml
import os
import json
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
COOKIES_PATH = os.path.join(os.path.dirname(__file__), "..", "linkedin_cookies.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def search_jobs() -> list[dict]:
    from playwright.sync_api import sync_playwright
    import requests as _r

    config = load_config()
    keywords = config["search"]["keywords"]
    cities = config["search"]["location"].get("cities", ["Salvador"])
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

        # Carrega cookies se existirem
        if os.path.exists(COOKIES_PATH):
            with open(COOKIES_PATH, encoding="utf-8") as f:
                ctx.add_cookies(json.load(f))

        page = ctx.new_page()

        search_targets = (
            [(kw, city, wt) for kw in keywords[:6] for city in cities for wt in ["1", "3"]] +
            [(kw, "Brasil", "2") for kw in keywords[:6]]  # remoto em todo Brasil
        )

        for keyword, city, wt in search_targets:
            try:
                url = (
                    "https://www.linkedin.com/jobs/search/"
                    f"?keywords={_r.utils.quote(keyword)}"
                    f"&location={_r.utils.quote(city)}"
                    f"&f_WT={wt}"
                    "&f_EA=true"
                    "&sortBy=DD"
                )
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                time.sleep(2)

                cards = page.locator("div.base-card, li.jobs-search-results__list-item").all()

                for card in cards:
                    try:
                        link = card.locator("a.base-card__full-link, a[href*='/jobs/view/']").first
                        if link.count() == 0:
                            continue
                        href = link.get_attribute("href") or ""
                        job_url = href.split("?")[0]
                        job_id = f"linkedin_{job_url.split('/')[-1]}"

                        if job_id in seen_ids or not job_url:
                            continue
                        seen_ids.add(job_id)

                        title = card.locator("h3.base-search-card__title, .job-card-list__title").first
                        company = card.locator("h4.base-search-card__subtitle, .job-card-container__company-name").first
                        location = card.locator("span.job-search-card__location, .job-card-container__metadata-item").first

                        mode_map = {"1": "on-site", "2": "remote", "3": "hybrid"}

                        jobs.append({
                            "id": job_id,
                            "title": title.inner_text().strip() if title.count() > 0 else keyword,
                            "company": company.inner_text().strip() if company.count() > 0 else "",
                            "location": location.inner_text().strip() if location.count() > 0 else city,
                            "mode": mode_map.get(wt, "on-site"),
                            "url": job_url,
                            "platform": "linkedin",
                            "description": "",
                        })
                    except Exception:
                        continue

                time.sleep(1.5)

            except Exception as e:
                print(f"[LinkedIn] Erro ao buscar '{keyword}' em '{city}': {e}")

        browser.close()

    print(f"[LinkedIn] {len(jobs)} vagas encontradas")
    return jobs
