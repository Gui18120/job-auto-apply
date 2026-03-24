"""
Aplica em vagas do Indeed via Playwright.
O Indeed tem dois fluxos:
  1. Candidatura no próprio Indeed (Indeed Apply) — automatizável
  2. Redireciona para site da empresa — abre o link e registra como manual_pending
"""
import yaml
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fill_common_fields(page, profile):
    """Preenche campos recorrentes no formulário do Indeed."""
    # Nome
    for label in ["name", "nome", "full name", "nome completo"]:
        f = page.locator(f'input[aria-label*="{label}" i], input[placeholder*="{label}" i]')
        if f.count() > 0 and not f.first.input_value():
            f.first.fill(profile.get("name", ""))

    # Telefone
    for label in ["phone", "telefone", "celular", "mobile"]:
        f = page.locator(f'input[aria-label*="{label}" i], input[placeholder*="{label}" i]')
        if f.count() > 0 and not f.first.input_value():
            f.first.fill(profile.get("phone", ""))

    # Cidade
    for label in ["city", "cidade", "location", "localização"]:
        f = page.locator(f'input[aria-label*="{label}" i], input[placeholder*="{label}" i]')
        if f.count() > 0 and not f.first.input_value():
            f.first.fill(profile.get("city", ""))


def apply(job: dict) -> bool:
    config = load_config()
    creds = config["accounts"]["indeed"]
    resume_path = config["resume"]["path"]
    profile = config["profile"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1. Login no Indeed
            page.goto("https://secure.indeed.com/auth", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            email_field = page.locator('input[name="email"], input[type="email"]')
            if email_field.count() > 0:
                email_field.first.fill(creds["email"])
                page.click('button[type="submit"]')
                time.sleep(2)

            password_field = page.locator('input[name="password"], input[type="password"]')
            if password_field.count() > 0:
                password_field.first.fill(creds["password"])
                page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle", timeout=15000)

            if "auth" in page.url or "login" in page.url:
                print("[Indeed] Verificação adicional necessária.")
                input("Resolva e pressione Enter para continuar...")

            # 2. Acessa a vaga
            page.goto(job["url"], timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 3. Verifica tipo de candidatura
            apply_btn = page.locator(
                'button:has-text("Candidatar-se agora"), '
                'button:has-text("Apply now"), '
                'a:has-text("Candidatar-se agora")'
            )

            if apply_btn.count() == 0:
                print(f"[Indeed] Botão de candidatura não encontrado: {job['url']}")
                browser.close()
                return False

            # Detecta se é "Indeed Apply" ou redirecionamento externo
            btn_href = apply_btn.first.get_attribute("href") or ""
            is_external = btn_href.startswith("http") and "indeed.com" not in btn_href

            if is_external:
                print(f"[Indeed] Vaga redireciona para site externo: {btn_href}")
                print(f"  -> Registrada como manual_pending: {job['title']}")
                browser.close()
                return False  # main.py vai tratar como manual_pending

            apply_btn.first.click()
            time.sleep(2)

            # 4. Fluxo Indeed Apply — itera pelos steps
            for step in range(8):
                # Upload de currículo
                upload = page.locator('input[type="file"]')
                if upload.count() > 0:
                    upload.first.set_input_files(resume_path)
                    time.sleep(1)

                # Preenche campos
                _fill_common_fields(page, profile)

                # Campos numéricos vazios → 0
                for field in page.locator('input[type="number"]').all():
                    if not field.input_value():
                        field.fill("0")

                # Botão de avançar/submeter
                next_btn = page.locator(
                    'button:has-text("Continuar"), button:has-text("Próximo"), '
                    'button:has-text("Enviar candidatura"), button:has-text("Submit")'
                )
                if next_btn.count() == 0:
                    break

                btn_text = next_btn.first.inner_text().strip()
                next_btn.first.click()
                time.sleep(2)

                if any(w in btn_text for w in ["Enviar", "Submit"]):
                    break

            # 5. Confirmação
            confirmado = page.locator(
                ':has-text("candidatura enviada"), :has-text("application submitted"), '
                ':has-text("sucesso")'
            ).count() > 0

            status = "enviada" if confirmado else "possivelmente enviada"
            print(f"[Indeed] Candidatura {status}: {job['title']} @ {job['company']}")
            browser.close()
            return True

        except PWTimeout:
            print(f"[Indeed] Timeout: {job['url']}")
            browser.close()
            return False
        except Exception as e:
            print(f"[Indeed] Erro: {e}")
            browser.close()
            return False
