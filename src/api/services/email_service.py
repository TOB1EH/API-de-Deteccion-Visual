import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "abrambilla804@alumnos.iua.edu.ar")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "abrambilla804@alumnos.iua.edu.ar")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "API Deteccion Visual")


def send_email(to: str, subject: str, body: str) -> bool:
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD no configurada, no se puede enviar email a %s", to)
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to], msg.as_string())
        server.quit()
        logger.info("Email enviado a %s: %s", to, subject)
        return True
    except Exception as e:
        logger.exception("Error enviando email a %s: %s", to, e)
        return False
