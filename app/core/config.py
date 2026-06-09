"""
Centralised configuration using Pydantic v2 BaseSettings.
Validates DATABASE_URL and environment.
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

# Chargement explicite du .env depuis la racine du projet
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ENV: Literal["dev", "test", "prod"] = "dev"
    DATABASE_URL: str = "sqlite+aiosqlite:///./wfm.db"  # SQLite par défaut pour le dev local
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.ENV == "prod"


settings = Settings()