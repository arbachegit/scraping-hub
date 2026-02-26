"""
Email service for sending verification and password reset emails.

Uses SMTP (aiosmtplib) for sending.
In development mode (no SMTP configured), logs the code to console.
"""

import structlog

from config.settings import settings

logger = structlog.get_logger()


async def _send_smtp(to_email: str, subject: str, body_html: str) -> bool:
    """
    Send an email via SMTP using aiosmtplib.

    Returns True if sent successfully, False otherwise.
    """
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["From"] = settings.email_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=False,
            start_tls=True,
        )
        logger.info("email_sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", to=to_email, error=str(e))
        return False


def _is_smtp_configured() -> bool:
    """Check if SMTP is properly configured."""
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


async def send_set_password_email(
    to_email: str, user_name: str, set_password_token: str
) -> bool:
    """
    Send an email with a link to set the initial password.

    Args:
        to_email: Recipient email.
        user_name: Name of the new user.
        set_password_token: JWT token for password setting.

    Returns:
        True if sent (or logged in dev mode).
    """
    subject = "IconsAI - Configure sua senha"
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Bem-vindo ao IconsAI, {user_name}!</h2>
        <p>Sua conta foi criada. Use o token abaixo para configurar sua senha:</p>
        <p style="background: #f0f0f0; padding: 12px; border-radius: 4px; font-family: monospace; word-break: break-all;">
            {set_password_token}
        </p>
        <p><strong>Este token expira em 24 horas.</strong></p>
        <p>Endpoint: <code>POST /auth/set-password</code></p>
        <hr>
        <p style="color: #666; font-size: 12px;">IconsAI - Inteligencia de Dados</p>
    </body>
    </html>
    """

    if not _is_smtp_configured():
        logger.info(
            "email_dev_mode",
            to=to_email,
            subject=subject,
            set_password_token=set_password_token,
            msg="SMTP not configured. Token logged for development.",
        )
        return True

    return await _send_smtp(to_email, subject, body_html)


async def send_verification_code_email(
    to_email: str, code: str, code_type: str
) -> bool:
    """
    Send a 6-digit verification code via email.

    Args:
        to_email: Recipient email.
        code: The 6-digit code.
        code_type: 'activation' or 'password_reset'.

    Returns:
        True if sent (or logged in dev mode).
    """
    type_label = "ativacao de conta" if code_type == "activation" else "recuperacao de senha"
    subject = f"IconsAI - Codigo de {type_label}"
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Codigo de Verificacao</h2>
        <p>Seu codigo para {type_label}:</p>
        <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                  background: #f0f0f0; padding: 16px; border-radius: 8px;
                  text-align: center;">
            {code}
        </p>
        <p><strong>Este codigo expira em 10 minutos.</strong></p>
        <p style="color: #666;">Se voce nao solicitou este codigo, ignore este email.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">IconsAI - Inteligencia de Dados</p>
    </body>
    </html>
    """

    if not _is_smtp_configured():
        logger.info(
            "email_dev_mode",
            to=to_email,
            code=code,
            code_type=code_type,
            msg="SMTP not configured. Code logged for development.",
        )
        return True

    return await _send_smtp(to_email, subject, body_html)


async def send_password_reset_email(
    to_email: str, reset_token: str
) -> bool:
    """
    Send a password reset email with a token.

    Args:
        to_email: Recipient email.
        reset_token: JWT token for password reset.

    Returns:
        True if sent (or logged in dev mode).
    """
    subject = "IconsAI - Recuperacao de Senha"
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Recuperacao de Senha</h2>
        <p>Voce solicitou a recuperacao de senha. Use o token abaixo:</p>
        <p style="background: #f0f0f0; padding: 12px; border-radius: 4px; font-family: monospace; word-break: break-all;">
            {reset_token}
        </p>
        <p><strong>Este token expira em 1 hora.</strong></p>
        <p>Endpoint: <code>POST /auth/reset-password</code></p>
        <p style="color: #666;">Se voce nao solicitou, ignore este email.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">IconsAI - Inteligencia de Dados</p>
    </body>
    </html>
    """

    if not _is_smtp_configured():
        logger.info(
            "email_dev_mode",
            to=to_email,
            reset_token=reset_token,
            msg="SMTP not configured. Token logged for development.",
        )
        return True

    return await _send_smtp(to_email, subject, body_html)
