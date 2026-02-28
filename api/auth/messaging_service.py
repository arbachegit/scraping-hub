"""
Messaging service for WhatsApp and SMS via Twilio (primary) and Infobip (fallback).

Dev mode: if neither Twilio nor Infobip are configured, messages are logged to console.
All sends are recorded in the messaging_logs table.
"""

import asyncio
from typing import Optional

import httpx
import structlog

from config.settings import settings
from src.database.client import get_supabase

logger = structlog.get_logger()


def _log_messaging(
    user_id: Optional[int],
    channel: str,
    provider: str,
    recipient: str,
    message_type: str,
    status: str,
    error_message: Optional[str] = None,
    provider_message_id: Optional[str] = None,
) -> None:
    """Record a messaging event in the messaging_logs table."""
    supabase = get_supabase()
    if not supabase:
        return
    try:
        supabase.table("messaging_logs").insert({
            "user_id": user_id,
            "channel": channel,
            "provider": provider,
            "recipient": recipient,
            "message_type": message_type,
            "status": status,
            "error_message": error_message,
            "provider_message_id": provider_message_id,
        }).execute()
    except Exception as e:
        logger.warning("messaging_log_insert_error", error=str(e))


class MessagingService:
    """Sends WhatsApp and SMS messages via Twilio (primary) + Infobip (fallback)."""

    def __init__(self) -> None:
        self._twilio_client = None

    @property
    def _is_dev_mode(self) -> bool:
        return not settings.has_twilio and not settings.has_infobip

    def _get_twilio_client(self):
        """Lazy-init Twilio client."""
        if self._twilio_client is None and settings.has_twilio:
            from twilio.rest import Client
            self._twilio_client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token,
            )
        return self._twilio_client

    # =============================================
    # WHATSAPP
    # =============================================

    async def send_whatsapp(
        self,
        phone: str,
        message: str,
        user_id: Optional[int] = None,
        message_type: str = "generic",
    ) -> bool:
        """Send WhatsApp message. Twilio primary, Infobip fallback."""
        if self._is_dev_mode:
            logger.info(
                "messaging_dev_mode",
                channel="whatsapp",
                phone=phone,
                message=message,
                message_type=message_type,
            )
            _log_messaging(user_id, "whatsapp", "dev", phone, message_type, "sent")
            return True

        # Try Twilio first
        if settings.has_twilio:
            try:
                result = await self._send_whatsapp_twilio(phone, message)
                _log_messaging(
                    user_id, "whatsapp", "twilio", phone, message_type, "sent",
                    provider_message_id=result,
                )
                return True
            except Exception as e:
                logger.warning("twilio_whatsapp_failed", phone=phone, error=str(e))
                _log_messaging(
                    user_id, "whatsapp", "twilio", phone, message_type, "failed",
                    error_message=str(e),
                )

        # Fallback to Infobip
        if settings.has_infobip:
            try:
                result = await self._send_whatsapp_infobip(phone, message)
                _log_messaging(
                    user_id, "whatsapp", "infobip", phone, message_type, "fallback",
                    provider_message_id=result,
                )
                return True
            except Exception as e:
                logger.error("infobip_whatsapp_failed", phone=phone, error=str(e))
                _log_messaging(
                    user_id, "whatsapp", "infobip", phone, message_type, "failed",
                    error_message=str(e),
                )

        logger.error("whatsapp_all_providers_failed", phone=phone)
        return False

    async def _send_whatsapp_twilio(self, phone: str, message: str) -> str:
        """Send WhatsApp via Twilio. Returns message SID."""
        client = self._get_twilio_client()
        if not client:
            raise RuntimeError("Twilio client not initialized")

        whatsapp_to = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
        whatsapp_from = settings.twilio_whatsapp_from

        msg = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=whatsapp_to,
        )
        logger.info("twilio_whatsapp_sent", sid=msg.sid, to=phone)
        return msg.sid

    async def _send_whatsapp_infobip(self, phone: str, message: str) -> str:
        """Send WhatsApp via Infobip. Returns message ID."""
        clean_phone = phone.replace("whatsapp:", "").lstrip("+")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.infobip_base_url}/whatsapp/1/message/text",
                headers={
                    "Authorization": f"App {settings.infobip_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.infobip_whatsapp_from,
                    "to": clean_phone,
                    "content": {"text": message},
                },
            )
            response.raise_for_status()
            data = response.json()
            msg_id = data.get("messages", [{}])[0].get("messageId", "")
            logger.info("infobip_whatsapp_sent", message_id=msg_id, to=phone)
            return msg_id

    # =============================================
    # SMS
    # =============================================

    async def send_sms(
        self,
        phone: str,
        message: str,
        user_id: Optional[int] = None,
        message_type: str = "generic",
    ) -> bool:
        """Send SMS. Twilio primary, Infobip fallback."""
        if self._is_dev_mode:
            logger.info(
                "messaging_dev_mode",
                channel="sms",
                phone=phone,
                message=message,
                message_type=message_type,
            )
            _log_messaging(user_id, "sms", "dev", phone, message_type, "sent")
            return True

        # Try Twilio first
        if settings.has_twilio:
            try:
                result = await self._send_sms_twilio(phone, message)
                _log_messaging(
                    user_id, "sms", "twilio", phone, message_type, "sent",
                    provider_message_id=result,
                )
                return True
            except Exception as e:
                logger.warning("twilio_sms_failed", phone=phone, error=str(e))
                _log_messaging(
                    user_id, "sms", "twilio", phone, message_type, "failed",
                    error_message=str(e),
                )

        # Fallback to Infobip
        if settings.has_infobip:
            try:
                result = await self._send_sms_infobip(phone, message)
                _log_messaging(
                    user_id, "sms", "infobip", phone, message_type, "fallback",
                    provider_message_id=result,
                )
                return True
            except Exception as e:
                logger.error("infobip_sms_failed", phone=phone, error=str(e))
                _log_messaging(
                    user_id, "sms", "infobip", phone, message_type, "failed",
                    error_message=str(e),
                )

        logger.error("sms_all_providers_failed", phone=phone)
        return False

    async def _send_sms_twilio(self, phone: str, message: str) -> str:
        """Send SMS via Twilio. Returns message SID."""
        client = self._get_twilio_client()
        if not client:
            raise RuntimeError("Twilio client not initialized")

        msg = client.messages.create(
            body=message,
            from_=settings.twilio_sms_from,
            to=phone,
        )
        logger.info("twilio_sms_sent", sid=msg.sid, to=phone)
        return msg.sid

    async def _send_sms_infobip(self, phone: str, message: str) -> str:
        """Send SMS via Infobip. Returns message ID."""
        clean_phone = phone.lstrip("+")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.infobip_base_url}/sms/2/text/advanced",
                headers={
                    "Authorization": f"App {settings.infobip_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [{
                        "from": settings.infobip_sms_from,
                        "destinations": [{"to": clean_phone}],
                        "text": message,
                    }]
                },
            )
            response.raise_for_status()
            data = response.json()
            msg_id = (
                data.get("messages", [{}])[0].get("messageId", "")
            )
            logger.info("infobip_sms_sent", message_id=msg_id, to=phone)
            return msg_id

    # =============================================
    # HIGH-LEVEL METHODS
    # =============================================

    async def send_invite(
        self,
        phone: str,
        user_name: str,
        set_password_url: str,
        user_id: Optional[int] = None,
    ) -> bool:
        """Send invite via WhatsApp + SMS simultaneously."""
        whatsapp_msg = (
            f"Ola {user_name}! Bem-vindo ao IconsAI.\n\n"
            f"Sua conta foi criada. Configure sua senha acessando:\n"
            f"{set_password_url}\n\n"
            f"Este link expira em 24 horas."
        )

        sms_msg = (
            f"IconsAI: Ola {user_name}! Configure sua senha: {set_password_url} "
            f"(expira em 24h)"
        )

        results = await asyncio.gather(
            self.send_whatsapp(phone, whatsapp_msg, user_id, "invite"),
            self.send_sms(phone, sms_msg, user_id, "invite"),
            return_exceptions=True,
        )

        success = any(r is True for r in results)
        if not success:
            logger.error("invite_messaging_all_failed", phone=phone, user_name=user_name)
        return success

    async def send_verification_code(
        self,
        phone: str,
        code: str,
        user_id: Optional[int] = None,
    ) -> bool:
        """Send 6-digit verification code via SMS only."""
        sms_msg = f"IconsAI: Seu codigo de verificacao e {code}. Expira em 10 minutos."
        return await self.send_sms(phone, sms_msg, user_id, "verification_code")

    async def send_password_reset(
        self,
        phone: str,
        code: str,
        user_id: Optional[int] = None,
    ) -> bool:
        """Send password reset code via SMS only."""
        sms_msg = f"IconsAI: Seu codigo de recuperacao de senha e {code}. Expira em 10 minutos."
        return await self.send_sms(phone, sms_msg, user_id, "password_reset")


# Singleton instance
messaging_service = MessagingService()
