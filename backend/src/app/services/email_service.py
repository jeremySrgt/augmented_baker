import logging
from email.message import EmailMessage

from app.config import settings
from app.repositories.smtp import SmtpRepository, get_smtp_repository

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, smtp: SmtpRepository) -> None:
        self._smtp = smtp

    def send(self, to: str, subject: str, body: str) -> str:
        recipient = settings.SMTP_REDIRECT_TO or to
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        if settings.SMTP_DRY_RUN:
            logger.info(
                "smtp dry-run -> %s (intended: %s): subject=%s; body_chars=%d",
                recipient, to, subject, len(body),
            )
            return recipient

        self._smtp.send(message)
        logger.info(
            "smtp sent -> %s (intended: %s): subject=%s",
            recipient, to, subject,
        )
        return recipient


email_service = EmailService(get_smtp_repository())


def get_email_service() -> EmailService:
    return email_service
