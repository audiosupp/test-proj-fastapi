"""
Настройки приложения.
Pydantic-settings автоматически загружает переменные из .env файла.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Типизированные настройки, доступные во всём приложении."""

    # AI
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"

    # Email / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@portfolio.dev"
    smtp_to: str = ""

    # Rate Limiting
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 3600

    # Общие
    app_name: str = "Portfolio API"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
