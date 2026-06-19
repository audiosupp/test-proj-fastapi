import json
import logging
import re
from typing import Any
import httpx

from app.core.config import settings
from app.schemas.contact_schema import AIAnalysis, Sentiment

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — ИИ-классификатор обращений. Твоя задача — проанализировать комментарий пользователя на русском языке.

Верни СТРОГО один JSON-объект. Не пиши никакого текста до или после JSON. Не используй разметку ```json.

Формат ответа строго такой (ключи на английском, значения на русском):
{"sentiment": "позитивный", "category": "вопрос"}

Допустимые значения для sentiment: позитивный, негативный, нейтральный.
Допустимые значения для category (примеры): оффер, сотрудничество, вопрос, фидбек, спам, общее.

Примеры:
Пользователь: "Мне очень нравится ваш сайт!" -> {"sentiment": "позитивный", "category": "фидбек"}
Пользователь: "Как с вами связаться по работе?" -> {"sentiment": "нейтральный", "category": "сотрудничество"}
Пользователь: "Все работает ужасно, исправьте!" -> {"sentiment": "негативный", "category": "фидбек"}
"""


class AIService:
    """Сервис для AI-анализа комментариев через OpenRouter."""

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key.strip()
        if not self.api_key:
            logger.warning(
                "OPENROUTER_API_KEY не указан — AI-анализ будет использовать fallback-значения.")

    async def analyze_comment(self, comment: str) -> AIAnalysis:
        """
        Анализирует комментарий пользователя через асинхронный HTTP-запрос к OpenRouter.
        При любой ошибке возвращает fallback (UNKNOWN / "общее").
        """
        fallback = AIAnalysis(sentiment=Sentiment.UNKNOWN, category="общее")

        if not self.api_key:
            logger.info("Пропускаем AI-запрос: не указан API-ключ.")
            return fallback

        try:
            model = settings.openrouter_model
            logger.info(f"Отправляем запрос в OpenRouter (модель: {model})")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": comment},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }

            # Используем httpx.AsyncClient для неблокирующего I/O
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    settings.openrouter_url, headers=headers, json=data
                )

            if response.status_code != 200:
                logger.error(
                    f"OpenRouter вернул ошибку {response.status_code}: {response.text}")
                return fallback

            result_json = response.json()

            # Извлекаем содержимое ответа
            raw_content = result_json['choices'][0]['message'].get('content', '')
            logger.info(f"СЫРОЙ ОТВЕТ AI: '{raw_content}'")

            if not raw_content:
                logger.warning("OpenRouter вернул пустой ответ.")
                return fallback

            # Парсим JSON
            parsed = self._parse_ai_json(raw_content)

            sentiment = self._normalize_sentiment(parsed.get("sentiment"))
            category = self._normalize_category(parsed.get("category"))

            return AIAnalysis(sentiment=sentiment, category=category)

        except Exception as exc:
            logger.error("Неожиданная ошибка AI-сервиса: %s", exc)
            return fallback

    @staticmethod
    def _parse_ai_json(raw: str) -> dict[str, Any]:
        """Извлекает JSON-объект из ответа модели, даже если есть лишний текст."""
        cleaned = raw.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "",
                             cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("AI вернул не-JSON содержимое: %s", raw[:200])
            return {}

    @staticmethod
    def _normalize_sentiment(value: Any) -> Sentiment:
        """Нормализует строку тональности в значение Enum."""
        if not isinstance(value, str):
            return Sentiment.UNKNOWN
        normalized = value.lower().strip()
        try:
            return Sentiment(normalized)
        except ValueError:
            return Sentiment.UNKNOWN

    @staticmethod
    def _normalize_category(value: Any) -> str:
        """Нормализует строку категории."""
        if not isinstance(value, str) or not value.strip():
            return "общее"
        return value.lower().strip()
