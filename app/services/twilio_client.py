# app/services/twilio_client.py
from typing import Optional

from twilio.rest import Client as TwilioSDKClient

from app.config import get_settings


class TwilioClient:
    """
    Thin wrapper around the Twilio Python SDK.

    This makes it easy to:
    - centralize config (account SID, auth token, from number, webhook URL)
    - mock in tests by replacing this class with a fake.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        voice_url: str,
    ):
        self._client = TwilioSDKClient(account_sid, auth_token)
        self._from_number = from_number
        self._voice_url = voice_url

    def create_outbound_call(self, to_number: str) -> str:
        """
        Create an outbound call via Twilio and return the Call SID.
        """
        call = self._client.calls.create(
            to=to_number,
            from_=self._from_number,
            url=self._voice_url,
        )
        return call.sid


def get_twilio_client() -> TwilioClient:
    """
    FastAPI dependency to get a configured TwilioClient.
    Raises RuntimeError if configuration is incomplete.
    """
    settings = get_settings()

    missing: list[str] = []
    if not settings.TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not settings.TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not settings.TWILIO_PHONE_NUMBER:
        missing.append("TWILIO_PHONE_NUMBER")
    if not settings.TWILIO_VOICE_WEBHOOK_URL:
        missing.append("TWILIO_VOICE_WEBHOOK_URL")

    if missing:
        raise RuntimeError(f"Twilio not configured, missing: {', '.join(missing)}")

    return TwilioClient(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_PHONE_NUMBER,
        voice_url=settings.TWILIO_VOICE_WEBHOOK_URL,
    )
