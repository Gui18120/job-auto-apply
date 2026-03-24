"""
Aplica para vagas que disponibilizam e-mail de contato.
"""
import smtplib
import yaml
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply(job: dict, recipient_email: str) -> bool:
    """
    Envia currículo por e-mail para uma vaga específica.
    job: dict com title, company, url
    recipient_email: e-mail de RH da empresa
    """
    config = load_config()
    profile = config["profile"]
    email_cfg = config["email"]
    resume_path = config["resume"]["path"]

    subject = f"Candidatura: {job['title']} | {profile['name']}"

    body = config["application"]["cover_message"].format(
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        email=profile["email"],
        phone=profile.get("phone", ""),
    )

    msg = MIMEMultipart()
    msg["From"] = email_cfg["sender"]
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Anexa o currículo PDF
    if os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(resume_path)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)
    else:
        print(f"[Email] Currículo não encontrado em: {resume_path}")
        return False

    try:
        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.starttls()
            server.login(email_cfg["sender"], email_cfg["app_password"])
            server.sendmail(email_cfg["sender"], recipient_email, msg.as_string())
        print(f"[Email] Candidatura enviada para {recipient_email} | {job['title']} @ {job['company']}")
        return True
    except Exception as e:
        print(f"[Email] Erro ao enviar para {recipient_email}: {e}")
        return False
