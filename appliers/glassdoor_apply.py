"""
Aplica em vagas do Glassdoor via Playwright.
Glassdoor geralmente redireciona para o site da empresa.
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
    resume_path = config["resume"]["path"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            page.goto(job["url"], timeout=60000)
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            time.sleep(3)

            # Verifica se vaga está encerrada
            if page.locator(':has-text("vaga encerrada"), :has-text("não está mais disponível"), :has-text("expirada")').count() > 0:
                print(f"[Glassdoor] Vaga encerrada, pulando: {job['url']}")
                browser.close()
                return False

            # Clica em candidatar
            apply_btn = page.locator(
                'button:has-text("Candidatar"), a:has-text("Candidatar"), '
                'button:has-text("Apply"), a:has-text("Apply"), '
                'button:has-text("Easy Apply")'
            )
            if apply_btn.count() == 0:
                print(f"[Glassdoor] Botão de candidatura não encontrado — registrado como manual_pending")
                browser.close()
                return False

            apply_btn.first.click()
            time.sleep(3)

            # Upload de currículo se solicitado
            upload = page.locator('input[type="file"]')
            if upload.count() > 0:
                upload.first.set_input_files(resume_path)
                time.sleep(1)

            # Avança nos passos do formulário
            for _ in range(5):
                next_btn = page.locator(
                    'button:has-text("Próximo"), button:has-text("Continuar"), '
                    'button:has-text("Enviar"), button:has-text("Submit"), '
                    'button:has-text("Next")'
                )
                if next_btn.count() == 0:
                    break
                next_btn.first.click()
                time.sleep(2)

            print(f"[Glassdoor] Candidatura enviada: {job['title']} @ {job['company']}")
            browser.close()
            return True

        except PWTimeout:
            print(f"[Glassdoor] Timeout na candidatura: {job['url']}")
            browser.close()
            return False
        except Exception as e:
            print(f"[Glassdoor] Erro: {e}")
            browser.close()
            return False
