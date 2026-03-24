"""
Orquestrador principal do sistema de candidatura automática.

Uso:
  python main.py            # roda uma vez agora
  python main.py --watch    # roda em loop (a cada N horas)
  python main.py --report   # mostra candidaturas enviadas
"""
import sys
import time
import yaml
import os
import schedule
import threading

from tracker import init_db, already_applied, save_application, print_report
from notifier import notify
from watchers.resume_watcher import start as start_resume_watcher

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_scraper(platform: str):
    if platform == "gupy":
        from scrapers.gupy import search_jobs
    elif platform == "linkedin":
        from scrapers.linkedin import search_jobs
    elif platform == "indeed":
        from scrapers.indeed import search_jobs
    elif platform == "catho":
        from scrapers.catho import search_jobs
    else:
        return None
    return search_jobs


def get_applier(platform: str):
    if platform == "gupy":
        from appliers.gupy_apply import apply
    elif platform == "linkedin":
        from appliers.linkedin_apply import apply
    elif platform == "catho":
        from appliers.catho_apply import apply
    elif platform == "indeed":
        from appliers.indeed_apply import apply
    else:
        return None
    return apply


def run_cycle():
    config = load_config()
    platforms = ["gupy", "linkedin", "indeed", "catho"]
    total_applied = 0

    print("\n" + "="*60)
    print("  INICIANDO CICLO DE BUSCA DE VAGAS")
    print("="*60)

    for platform in platforms:
        scraper = get_scraper(platform)
        if not scraper:
            continue

        print(f"\n[Main] Buscando vagas no {platform.upper()}...")
        try:
            jobs = scraper()
        except Exception as e:
            print(f"[Main] Erro ao buscar {platform}: {e}")
            continue

        new_jobs = [j for j in jobs if not already_applied(j["id"])]

        # Filtro de localização: presencial só em Salvador/BA; remoto/híbrido em qualquer lugar
        def location_ok(job):
            mode = job.get("mode", "").lower()
            location = job.get("location", "").lower()
            if mode in ("remote", "remoto", "home office"):
                return True
            if mode in ("hybrid", "híbrido", "hibrido"):
                return True
            # presencial: só aceita Salvador ou BA
            if "salvador" in location or (", ba" in location) or ("bahia" in location):
                return True
            return False

        filtered_jobs = [j for j in new_jobs if location_ok(j)]
        skipped = len(new_jobs) - len(filtered_jobs)
        print(f"[Main] {len(filtered_jobs)} vagas novas no {platform.upper()} ({skipped} fora de Salvador ignoradas)")

        applier = get_applier(platform)

        for job in filtered_jobs:
            if not job.get("title") or not job.get("url"):
                continue

            # Verifica se a vaga ainda existe (evita 404)
            try:
                check = __import__("requests").head(job["url"], timeout=(5, 8), allow_redirects=True)
                if check.status_code == 404:
                    print(f"  [!] Vaga encerrada (404), pulando: {job['url']}")
                    save_application(job_id=job["id"], job_title=job["title"], company=job["company"],
                                     platform=platform, url=job["url"], location=job.get("location", ""),
                                     mode=job.get("mode", ""), status="closed")
                    continue
            except Exception:
                pass

            print(f"\n  -> {job['title']} @ {job['company']} | {job.get('mode', '')} | {job.get('location', '')}")
            print(f"     URL: {job['url']}")

            success = False

            if applier:
                try:
                    success = applier(job)
                except Exception as e:
                    print(f"[Main] Erro ao candidatar ({platform}): {e}")
            else:
                # Plataforma sem applier automático: só registra para revisão manual
                print(f"  [!] {platform.upper()} sem applier automático. Registrado para candidatura manual.")
                success = True  # salva no tracker como 'manual_pending'
                save_application(
                    job_id=job["id"],
                    job_title=job["title"],
                    company=job["company"],
                    platform=platform,
                    url=job["url"],
                    location=job.get("location", ""),
                    mode=job.get("mode", ""),
                    status="manual_pending",
                )
                notify("Vaga para candidatura manual",
                       f"{job['title']} @ {job['company']} ({platform})")
                continue

            if success:
                save_application(
                    job_id=job["id"],
                    job_title=job["title"],
                    company=job["company"],
                    platform=platform,
                    url=job["url"],
                    location=job.get("location", ""),
                    mode=job.get("mode", ""),
                    status="applied",
                )
                notify("Candidatura enviada!",
                       f"{job['title']} @ {job['company']} ({platform})")
                total_applied += 1
                time.sleep(3)  # pausa entre candidaturas

    print(f"\n[Main] Ciclo concluido. {total_applied} candidatura(s) enviada(s).\n")
    return total_applied


def main():
    init_db()
    config = load_config()
    args = sys.argv[1:]

    if "--report" in args:
        print_report()
        return

    resume_path = config["resume"]["path"]

    if "--watch" in args:
        interval_hours = config["schedule"].get("check_interval_hours", 2)

        # Inicia monitoramento do currículo em thread separada
        observer = start_resume_watcher(resume_path)

        print(f"[Main] Modo watch ativado. Checando vagas a cada {interval_hours}h.")
        print("[Main] Pressione Ctrl+C para parar.\n")

        run_cycle()  # roda imediatamente na primeira vez

        schedule.every(interval_hours).hours.do(run_cycle)

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n[Main] Encerrando...")
            observer.stop()
            observer.join()
    else:
        # Roda uma vez
        start_resume_watcher(resume_path)
        run_cycle()


if __name__ == "__main__":
    main()
