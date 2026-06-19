"""
Pydantic-схемы — аналог Zod-схем в TypeScript.

Валидируют входные данные в рантайме И генерируют OpenAPI-документацию.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class Sentiment(str, Enum):
    POSITIVE = "позитивный"
    NEGATIVE = "негативный"
    NEUTRAL = "нейтральный"
    UNKNOWN = "неопределен"


class ContactCreate(BaseModel):
    """
    Тело запроса для POST /api/contact.
    Аналог TypeScript-интерфейса с runtime-валидацией.
    """

    name: str = Field(..., min_length=2, max_length=100, examples=["Jane Doe"])
    phone: str = Field(..., min_length=7, max_length=20, examples=["+1 555 123 4567"])
    email: EmailStr = Field(..., examples=["jane@example.com"])
    comment: str = Field(..., min_length=10, max_length=2000, examples=["I'd love to discuss a Vue project."])

    @field_validator("name", "phone", "comment")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class AIAnalysis(BaseModel):
    """Структурированный ответ от AI-сервиса (тональность + категория)."""

    sentiment: Sentiment = Sentiment.UNKNOWN
    category: str = "общее"


class ContactResponse(BaseModel):
    """Ответ при успешной отправке формы обратной связи."""

    success: bool = True
    message: str
    sentiment: Sentiment
    category: str


class HealthResponse(BaseModel):
    """Проверка здоровья сервиса — аналог { status: 'ok' }."""

    status: str = "ok"
    service: str = "portfolio-api"


class MetricsResponse(BaseModel):
    """Агрегированная статистика обращений из metrics.json."""

    total_contacts: int
    sentiments: dict[str, int]
    categories: dict[str, int]


class ErrorResponse(BaseModel):
    """Стандартная структура ошибки для 4xx/5xx ответов."""

    detail: str
    errors: list[Any] | None = None
