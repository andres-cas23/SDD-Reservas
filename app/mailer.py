import smtplib
from email.message import EmailMessage

from app.config import Settings


def send_verification_email(settings: Settings, recipient: str, link: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Verifica tu cuenta"
    message["From"] = settings.smtp_sender
    message["To"] = recipient
    message.set_content(
        "Para verificar tu cuenta, abre este enlace. Si no solicitaste la cuenta, "
        "puedes ignorar este mensaje.\n\n"
        f"{link}\n"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        username = settings.smtp_username
        if username:
            smtp.login(username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
