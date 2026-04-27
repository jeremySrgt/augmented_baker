import logging
import smtplib
from email.message import EmailMessage

from app.repositories.smtp.client import open_smtp_connection

logger = logging.getLogger(__name__)


class EmailUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SmtpRepository:
    def send(self, message: EmailMessage) -> None:
        try:
            with open_smtp_connection() as smtp:
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("smtp send failed: %s", type(exc).__name__)
            raise EmailUnavailable("Serveur SMTP injoignable") from exc


smtp_repository = SmtpRepository()


def get_smtp_repository() -> SmtpRepository:
    return smtp_repository
