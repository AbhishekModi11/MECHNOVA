import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    BACKEND_API_URL: str = "http://127.0.0.1:8000/api"
    BACKEND_WS_URL: str = "ws://127.0.0.1:8000/ws"
    DEMO_SPEED_FACTOR: float = 10.0
    PORT: int = 8080
    STORAGE_SECRET: str = "supersecretstoragekey_mechnova_2026"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = FrontendSettings()
