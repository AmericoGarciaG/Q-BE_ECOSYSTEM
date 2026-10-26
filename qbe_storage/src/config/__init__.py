"""Configuración compartida del ecosistema (settings Pydantic)."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    ENVIRONMENT: str = "development"

    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Gemini API keys pool
    Gemini_API_4_QBE_001: str = ""
    Gemini_API_4_QBE_002: str = ""
    Gemini_API_4_QBE_003: str = ""
    Gemini_API_4_QBE_004: str = ""

    DATABASE_URL: str = "sqlite:///data/qbe_database.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
