import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.schemas.contact_schema import AIAnalysis, ContactCreate

logger = logging.getLogger(__name__)


class EmailService:
    """
    Сервис для отправки email-уведомлений о новых обращениях.
    """

    def __init__(self) -> None:
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from
        self.smtp_to = settings.smtp_to

    @property
    def is_configured(self) -> bool:
        """Проверяет, настроен ли SMTP (хост и получатель указаны)."""
        return bool(self.smtp_host and self.smtp_to)

    async def send_contact_notification(
        self,
        contact: ContactCreate,
        analysis: AIAnalysis,
    ) -> bool:
        """
        Отправляет два email-уведомления:
        1. Владельцу сайта — с данными обращения и AI-анализом.
        2. Пользователю — копию обращения.
        """
        # Письмо владельцу сайта
        owner_subject = f"Новое обращение от {contact.name}"
        owner_body = (
            f"Привет! На твоём сайте-портфолио оставили заявку.\n\n"
            f"Имя: {contact.name}\n"
            f"Email: {contact.email}\n"
            f"Телефон: {contact.phone}\n"
            f"Комментарий:\n{contact.comment}\n\n"
            f"--- ИИ Анализ обращения ---\n"
            f"Тональность: {analysis.sentiment.value}\n"
            f"Категория: {analysis.category}\n"
        )

        # Письмо-копия пользователю
        user_subject = f"Копия вашего обращения к разработчику {contact.name}"
        user_body = (
            f"Здравствуйте, {contact.name}!\n"
            f"Это автоматическая копия вашего обращения, оставленного на сайте-портфолио.\n\n"
            f"Ваш комментарий:\n\"{contact.comment}\"\n\n"
            f"Наш ИИ-ассистент уже проанализировал ваш запрос (Тональность: {analysis.sentiment.value}) "
            f"и передал его владельцу. Мы свяжемся с вами в ближайшее время!\n"
        )

        if not self.is_configured:
            logger.info(
                "SMTP не настроен — имитация отправки писем владельцу и пользователю.")
            return True

        try:
            # Отправляем письмо владельцу
            self._send_single_mail(self.smtp_to, owner_subject, owner_body)
            logger.info("Письмо отправлено владельцу: %s", self.smtp_to)

            # Отправляем копию пользователю
            self._send_single_mail(contact.email, user_subject, user_body)
            logger.info("Копия письма отправлена пользователю: %s",
                        contact.email)

            return True

        except smtplib.SMTPException as exc:
            logger.error("Ошибка SMTP при отправке письма: %s", exc)
            return False
        except OSError as exc:
            logger.error("Сетевая ошибка при отправке письма: %s", exc)
            return False

    @staticmethod
    def _send_single_mail(to_email: str, subject: str, body: str) -> None:
        """Формирует и отправляет одно email-письмо через SMTP."""
        from app.core.config import settings as s

        message = MIMEMultipart()
        message["From"] = s.smtp_from
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as server:
            server.starttls()
            if s.smtp_user and s.smtp_password:
                server.login(s.smtp_user, s.smtp_password)
            server.sendmail(s.smtp_from, [to_email], message.as_string())
