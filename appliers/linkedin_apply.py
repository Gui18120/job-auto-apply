"""
Aplica em vagas do LinkedIn via Easy Apply (Playwright).
"""
import yaml
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fill_text_fields(page, profile):
    """Preenche campos de texto comuns no formulário do LinkedIn."""
    fields = {
        "phone": profile.get("phone", ""),
        "telefone": profile.get("phone", ""),
        "city": profile.get("city", ""),
        "cidade": profile.get("city", ""),
    }
    for label_text, value in fields.items():
        if not value:
            continue
        field = page.locator(f'input[aria-label*="{label_text}" i]')
        if field.count() > 0:
            field.first.fill(value)


def apply(job: dict) -> bool:
    config = load_config()
    creds = config["accounts"]["linkedin"]
    resume_path = config["resume"]["path"]
    profile = config["profile"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1. Login no LinkedIn
            page.goto("https://www.linkedin.com/login", timeout=20000)
            page.fill('#username', creds["email"])
            page.fill('#password', creds["password"])
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=20000)

            if "checkpoint" in page.url or "login" in page.url:
                print("[LinkedIn] Verificação extra necessária. Conclua manualmente e reexecute.")
                input("Pressione Enter após resolver o captcha/verificação...")

            # 2. Acessa a vaga
            page.goto(job["url"], timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 3. Clica em Candidatura Simplificada (Easy Apply)
            easy_btn = page.locator('button:has-text("Candidatura simplificada")')
            if easy_btn.count() == 0:
                # Tenta em inglês também
                easy_btn = page.locator('button:has-text("Easy Apply")')

            if easy_btn.count() == 0:
                print(f"[LinkedIn] Sem Easy Apply para: {job['title']}")
                browser.close()
                return False

            easy_btn.first.click()
            time.sleep(2)

            # 4. Itera pelos passos do formulário (até 7 steps)
            for step in range(7):
                # Upload de currículo se aparecer
                upload = page.locator('input[type="file"]')
                if upload.count() > 0:
                    upload.first.set_input_files(resume_path)
                    time.sleep(1)

                # Preenche campos de texto
                _fill_text_fields(page, profile)

                # Responde perguntas numéricas com 0 se vazio
                numeric_fields = page.locator('input[type="number"]')
                for i in range(numeric_fields.count()):
                    field = numeric_fields.nth(i)
                    if field.input_value() == "":
                        field.fill("0")

                # Botão de próximo / submeter
                next_btn = page.locator(
                    'button:has-text("Próxima"), button:has-text("Próximo"), '
                    'button:has-text("Revisar"), button:has-text("Enviar candidatura")'
                )
                if next_btn.count() == 0:
                    break

                btn_text = next_btn.first.inner_text().strip()
                next_btn.first.click()
                time.sleep(2)

                if "Enviar" in btn_text or "Submit" in btn_text:
                    break

            # 5. Descarta popup de confirmação se aparecer
            dismiss = page.locator('button:has-text("Dispensar"), button[aria-label*="Dispensar"]')
            if dismiss.count() > 0:
                dismiss.first.click()

            print(f"[LinkedIn] Easy Apply enviado: {job['title']} @ {job['company']}")
            browser.close()
            return True

        except PWTimeout:
            print(f"[LinkedIn] Timeout: {job['url']}")
            browser.close()
            return False
        except Exception as e:
            print(f"[LinkedIn] Erro: {e}")
            browser.close()
            return False
