"""
Aplica em vagas do Catho via Playwright.
"""
import yaml
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply(job: dict) -> bool:
    config = load_config()
    creds = config["accounts"]["catho"]
    resume_path = config["resume"]["path"]
    profile = config["profile"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1. Login no Catho
            page.goto("https://seguro.catho.com.br/login/", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            page.fill('input[name="email"], input[type="email"]', creds["email"])
            page.fill('input[name="password"], input[type="password"]', creds["password"])
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=15000)

            if "login" in page.url or "entrar" in page.url:
                print("[Catho] Falha no login. Verifique email/senha no config.yaml")
                browser.close()
                return False

            # 2. Navega para a vaga
            page.goto(job["url"], timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 3. Clica em Candidatar-se
            apply_btn = page.locator(
                'button:has-text("Candidatar"), a:has-text("Candidatar"), '
                'button:has-text("Enviar currículo"), a:has-text("Enviar currículo")'
            )
            if apply_btn.count() == 0:
                print(f"[Catho] Botão de candidatura não encontrado: {job['url']}")
                browser.close()
                return False

            apply_btn.first.click()
            time.sleep(2)

            # 4. Upload de currículo se solicitado
            upload = page.locator('input[type="file"]')
            if upload.count() > 0:
                upload.first.set_input_files(resume_path)
                time.sleep(1)

            # 5. Avança pelos steps do formulário
            for _ in range(5):
                next_btn = page.locator(
                    'button:has-text("Próximo"), button:has-text("Continuar"), '
                    'button:has-text("Enviar"), button:has-text("Confirmar"), '
                    'button:has-text("Finalizar")'
                )
                if next_btn.count() == 0:
                    break
                btn_text = next_btn.first.inner_text().strip()
                next_btn.first.click()
                time.sleep(2)
                if any(w in btn_text for w in ["Enviar", "Confirmar", "Finalizar"]):
                    break

            # 6. Verifica confirmação
            confirmado = page.locator(
                ':has-text("candidatura enviada"), :has-text("currículo enviado"), '
                ':has-text("sucesso"), :has-text("cadastrado")'
            ).count() > 0

            status = "enviada" if confirmado else "possivelmente enviada"
            print(f"[Catho] Candidatura {status}: {job['title']} @ {job['company']}")
            browser.close()
            return True

        except PWTimeout:
            print(f"[Catho] Timeout: {job['url']}")
            browser.close()
            return False
        except Exception as e:
            print(f"[Catho] Erro: {e}")
            browser.close()
            return False
