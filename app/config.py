# app/config.py
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "dev"
    APP_NAME: str = "Alta AI Call Center MVP"

    # DB URL – for now SQLite local
    DATABASE_URL: str = "sqlite:///./app.db"

    # Twilio config
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # our Twilio caller ID
    TWILIO_WEBHOOK_SECRET: Optional[str] = None

    # NEW: where Twilio should fetch TwiML for the call
    TWILIO_VOICE_WEBHOOK_URL: Optional[str] = None

    # NEW: OpenAI integration (optional)
    # This will happily read OPENAI_API_KEY or openai_api_key from the env.
    openai_api_key: Optional[str] = None
    enable_openai: bool = False  # gate so tests never call OpenAI by accident
    openai_model: str = "gpt-4.1-mini"  # can be changed later

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings