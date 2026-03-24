"""
Monitora o currículo PDF. Quando detecta uma versão nova (por data de modificação),
atualiza automaticamente o currículo no perfil do LinkedIn.
"""
import os
import time
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def update_linkedin_resume(resume_path: str):
    """Faz upload do currículo atualizado no perfil do LinkedIn."""
    config = load_config()
    creds = config["accounts"]["linkedin"]

    print(f"[ResumeWatcher] Novo currículo detectado. Atualizando LinkedIn...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Login
            page.goto("https://www.linkedin.com/login", timeout=20000)
            page.fill('#username', creds["email"])
            page.fill('#password', creds["password"])
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=20000)

            if "checkpoint" in page.url or "login" in page.url:
                print("[LinkedIn] Verificação extra necessária.")
                input("Resolva a verificação e pressione Enter...")

            # Vai para a seção de currículo do perfil
            page.goto("https://www.linkedin.com/in/me/", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Abre modal "Mais" para achar a opção de currículo
            # (LinkedIn muda o layout com frequência — esse é o caminho mais estável)
            page.goto("https://www.linkedin.com/jobs/", timeout=20000)
            page.wait_for_load_state("networkidle")

            # Tenta upload via página de preferências de candidatura
            page.goto(
                "https://www.linkedin.com/jobs/tracker/applied/",
                timeout=20000,
            )
            time.sleep(2)

            upload = page.locator('input[type="file"]')
            if upload.count() > 0:
                upload.first.set_input_files(resume_path)
                time.sleep(2)
                save_btn = page.locator('button:has-text("Salvar"), button:has-text("Save")')
                if save_btn.count() > 0:
                    save_btn.first.click()
                print("[LinkedIn] Currículo atualizado no perfil!")
            else:
                print("[LinkedIn] Campo de upload não encontrado. Verifique manualmente.")

            browser.close()

        except Exception as e:
            print(f"[LinkedIn] Erro ao atualizar currículo: {e}")
            browser.close()


class ResumeHandler(FileSystemEventHandler):
    def __init__(self, resume_path: str):
        self.resume_path = os.path.abspath(resume_path)
        self.last_modified = os.path.getmtime(self.resume_path)

    def on_modified(self, event):
        if os.path.abspath(event.src_path) != self.resume_path:
            return
        new_mtime = os.path.getmtime(self.resume_path)
        if new_mtime == self.last_modified:
            return
        self.last_modified = new_mtime
        print(f"[ResumeWatcher] Currículo modificado: {self.resume_path}")
        time.sleep(1)  # aguarda o arquivo fechar
        update_linkedin_resume(self.resume_path)


def start(resume_path: str):
    resume_path = os.path.abspath(resume_path)
    watch_dir = os.path.dirname(resume_path)
    handler = ResumeHandler(resume_path)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()
    print(f"[ResumeWatcher] Monitorando: {resume_path}")
    return observer
