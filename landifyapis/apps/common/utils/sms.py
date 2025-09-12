from typing import Any, Dict

from django.conf import settings
from twilio.rest import Client

import logging
logger = logging.getLogger(__name__)

def send_sms(to_phone_number: str, message_body: str) -> Dict[str, Any]:
    """Gửi tin nhắn SMS qua Twilio."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        error_msg = "Cấu hình Twilio bị thiếu trong settings.py."
        logger.error(error_msg)
        return {"error": error_msg}

    try:
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = twilio_client.messages.create(
            body=message_body, from_=settings.TWILIO_PHONE_NUMBER, to=to_phone_number
        )
        return {"message": "SMS sent successfully", "sid": message.sid}
    except Exception as e:
        logger.error("Lỗi Twilio: %s", e)
        return {"error": str(e)}
