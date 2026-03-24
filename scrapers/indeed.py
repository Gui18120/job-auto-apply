"""
Scraper para vagas no Indeed Brasil via Playwright.
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
            ),
            locale="pt-BR",
        )
        page = ctx.new_page()

        search_targets = [(kw, city) for kw in keywords[:5] for city in cities] + \
                         [(kw, "") for kw in keywords[:5]]  # sem cidade = remoto

        for keyword, city in search_targets:
            try:
                import requests as _r
                params = f"q={_r.utils.quote(keyword)}&sort=date&fromage=30"
                if city:
                    params += f"&l={_r.utils.quote(city)}"
                url = f"https://br.indeed.com/jobs?{params}"

                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                time.sleep(2)

                cards = page.locator("div.job_seen_beacon, div[data-jk]").all()

                for card in cards:
                    try:
                        raw_id = card.get_attribute("data-jk") or ""
                        if not raw_id:
                            link = card.locator("a[data-jk]").first
                            raw_id = link.get_attribute("data-jk") or "" if link.count() > 0 else ""

                        if not raw_id:
                            continue

                        job_id = f"indeed_{raw_id}"
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)

                        title = card.locator("h2.jobTitle span[title], h2.jobTitle").first
                        company = card.locator("span.companyName, [data-testid='company-name']").first
                        location = card.locator("div.companyLocation, [data-testid='text-location']").first

                        title_text = title.inner_text().strip() if title.count() > 0 else keyword
                        company_text = company.inner_text().strip() if company.count() > 0 else ""
                        location_text = location.inner_text().strip() if location.count() > 0 else city

                        mode = "remote" if not city or "remoto" in location_text.lower() or "home office" in location_text.lower() else "on-site"

                        jobs.append({
                            "id": job_id,
                            "title": title_text,
                            "company": company_text,
                            "location": location_text,
                            "mode": mode,
                            "url": f"https://br.indeed.com/viewjob?jk={raw_id}",
                            "platform": "indeed",
                            "description": "",
                        })
                    except Exception:
                        continue

                time.sleep(2)

            except Exception as e:
                print(f"[Indeed] Erro ao buscar '{keyword}' em '{city}': {e}")

        browser.close()

    print(f"[Indeed] {len(jobs)} vagas encontradas")
    return jobs
