"""
Scraper para vagas no Glassdoor via Playwright (JS-heavy).
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

    search_locations = ["Salvador, Bahia", "Brasil", "Remote"]

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

        for keyword in keywords[:4]:
            for location in search_locations:
                try:
                    url = (
                        "https://www.glassdoor.com.br/Emprego/vagas.htm"
                        f"?sc.keyword={keyword.replace(' ', '+')}"
                        f"&locT=N&locKeyword={location.replace(' ', '+')}"
                        "&sortBy=date_desc"
                    )
                    page.goto(url, timeout=30000)
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    time.sleep(2)

                    cards = page.locator("li[data-test='jobListing'], article.job-listing").all()

                    for card in cards:
                        try:
                            link = card.locator("a").first
                            href = link.get_attribute("href") or ""
                            title = card.locator("[data-test='job-title'], .job-title").first
                            company = card.locator("[data-test='employer-name'], .employer-name").first
                            loc = card.locator("[data-test='emp-location'], .location").first

                            if not href:
                                continue

                            job_url = "https://www.glassdoor.com.br" + href if href.startswith("/") else href
                            job_id = f"glassdoor_{abs(hash(job_url))}"

                            if job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)

                            title_text = title.inner_text() if title.count() > 0 else keyword
                            company_text = company.inner_text() if company.count() > 0 else ""
                            loc_text = loc.inner_text() if loc.count() > 0 else location
                            mode = "remote" if "remoto" in loc_text.lower() or "remote" in location.lower() else "on-site"

                            jobs.append({
                                "id": job_id,
                                "title": title_text.strip(),
                                "company": company_text.strip(),
                                "location": loc_text.strip(),
                                "mode": mode,
                                "url": job_url,
                                "platform": "glassdoor",
                                "description": "",
                            })
                        except Exception:
                            continue

                    time.sleep(2)

                except Exception as e:
                    print(f"[Glassdoor] Erro ao buscar '{keyword}' em '{location}': {e}")

        browser.close()

    print(f"[Glassdoor] {len(jobs)} vagas encontradas")
    return jobs
