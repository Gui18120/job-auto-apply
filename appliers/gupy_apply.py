"""
Aplica em vagas do Gupy via Playwright.
Faz login, abre a página da vaga e completa a candidatura.
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
    creds = config["accounts"]["gupy"]
    resume_path = config["resume"]["path"]
    profile = config["profile"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # False para debugar; mude para True depois
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1. Vai direto para a vaga
            page.goto(job["url"], timeout=60000)
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            time.sleep(3)

            # 2. Se pedir login, faz login na página da empresa
            if page.locator('input[name="email"]').count() > 0:
                page.fill('input[name="email"]', creds["email"])
                page.fill('input[name="password"]', creds["password"])
                page.click('button[type="submit"]')
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                time.sleep(3)

            # 3. Se ainda redirecionar para login, tenta pelo portal geral
            if "login" in page.url or page.locator('input[name="email"]').count() > 0:
                page.goto("https://portal.gupy.io/login", timeout=60000)
                page.wait_for_selector('input[name="email"]', timeout=30000)
                page.fill('input[name="email"]', creds["email"])
                page.fill('input[name="password"]', creds["password"])
                page.click('button[type="submit"]')
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                time.sleep(3)
                page.goto(job["url"], timeout=60000)
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                time.sleep(3)

            # 3. Verifica se a vaga está encerrada
            if page.locator(':has-text("Candidaturas encerradas"), :has-text("vaga encerrada"), :has-text("encerrada")').count() > 0:
                print(f"[Gupy] Vaga encerrada, pulando: {job['url']}")
                browser.close()
                return False

            # 4. Clica em Candidatar-se
            apply_btn = page.locator('button:has-text("Candidatar"), a:has-text("Candidatar")')
            if apply_btn.count() == 0:
                print(f"[Gupy] Botão de candidatura não encontrado: {job['url']}")
                return False

            apply_btn.first.click()
            time.sleep(2)

            # 4. Upload do currículo se solicitado
            upload = page.locator('input[type="file"]')
            if upload.count() > 0:
                upload.first.set_input_files(resume_path)
                time.sleep(1)

            # 5. Tenta avançar/submeter os passos do formulário
            for _ in range(5):
                next_btn = page.locator(
                    'button:has-text("Próximo"), button:has-text("Continuar"), '
                    'button:has-text("Enviar"), button:has-text("Finalizar")'
                )
                if next_btn.count() == 0:
                    break
                next_btn.first.click()
                time.sleep(2)

            # 6. Confirmação
            if page.locator(':has-text("candidatura enviada"), :has-text("sucesso")').count() > 0:
                print(f"[Gupy] Candidatura enviada: {job['title']} @ {job['company']}")
                browser.close()
                return True

            print(f"[Gupy] Candidatura pode ter sido enviada (sem confirmação clara): {job['url']}")
            browser.close()
            return True

        except PWTimeout:
            print(f"[Gupy] Timeout na candidatura: {job['url']}")
            browser.close()
            return False
        except Exception as e:
            print(f"[Gupy] Erro: {e}")
            browser.close()
            return False
