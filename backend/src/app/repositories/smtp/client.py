from smtplib import SMTP

from app.config import settings


def open_smtp_connection() -> SMTP:
    smtp = SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
    if settings.SMTP_USE_TLS:
        smtp.starttls()
    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.get_secret_value())
    return smtp
