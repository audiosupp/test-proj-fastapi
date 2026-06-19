"""
Слой репозитория — читает/пишет JSON-файлы на диске.

Сервисный слой запрашивает данные; репозиторий занимается деталями хранения.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.contact_schema import Sentiment

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
METRICS_FILE = STORAGE_DIR / "metrics.json"
RATE_LIMITS_FILE = STORAGE_DIR / "rate_limits.json"
LOG_FILE = STORAGE_DIR / "app.log"


def _ensure_storage() -> None:
    """Создаёт директорию storage и файлы-заглушки, если их нет."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if not METRICS_FILE.exists():
        METRICS_FILE.write_text(
            json.dumps(
                {
                    "total_contacts": 0,
                    "sentiments": {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0},
                    "categories": {},
                },
                indent=2,
            )
        )

    if not RATE_LIMITS_FILE.exists():
        RATE_LIMITS_FILE.write_text("{}")


def _read_json(path: Path) -> dict[str, Any]:
    """Безопасно читает JSON-файл, возвращает пустой словарь при ошибке."""
    _ensure_storage()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Не удалось прочитать %s: %s", path, exc)
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Записывает JSON-файл."""
    _ensure_storage()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class MetricsRepository:
    """Хранилище метрик на основе файла — замена БД."""

    def get_metrics(self) -> dict[str, Any]:
        data = _read_json(METRICS_FILE)
        return {
            "total_contacts": data.get("total_contacts", 0),
            "sentiments": data.get(
                "sentiments",
                {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0},
            ),
            "categories": data.get("categories", {}),
        }

    def record_contact(self, sentiment: Sentiment, category: str) -> dict[str, Any]:
        """Увеличивает счётчики после успешной отправки формы."""
        data = _read_json(METRICS_FILE)

        data["total_contacts"] = data.get("total_contacts", 0) + 1

        sentiments: dict[str, int] = data.setdefault(
            "sentiments",
            {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0},
        )
        sentiment_key = sentiment.value
        sentiments[sentiment_key] = sentiments.get(sentiment_key, 0) + 1

        categories: dict[str, int] = data.setdefault("categories", {})
        normalized_category = category.lower().strip()
        categories[normalized_category] = categories.get(normalized_category, 0) + 1

        _write_json(METRICS_FILE, data)
        return self.get_metrics()


class RateLimitRepository:
    """
    Простой rate limiter со скользящим окном на основе JSON-файла.

    Для каждого IP хранится список временных меток запросов;
    старые записи удаляются при каждой проверке.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """
        Возвращает (allowed, retry_after_seconds).
        retry_after_seconds = 0 если запрос разрешён,
        иначе количество секунд до следующего слота.
        """
        now = datetime.now(timezone.utc)
        data = _read_json(RATE_LIMITS_FILE)

        timestamps: list[str] = data.get(client_ip, [])
        cutoff = now.timestamp() - self.window_seconds

        # Оставляем только метки в пределах текущего окна
        recent = [ts for ts in timestamps if datetime.fromisoformat(ts).timestamp() > cutoff]

        if len(recent) >= self.max_requests:
            oldest = datetime.fromisoformat(recent[0])
            retry_after = int(self.window_seconds - (now - oldest).total_seconds()) + 1
            return False, max(retry_after, 1)

        recent.append(now.isoformat())
        data[client_ip] = recent
        _write_json(RATE_LIMITS_FILE, data)
        return True, 0


class LogRepository:
    """Логгер, дописывающий сообщения в файл."""

    @staticmethod
    def log(message: str) -> None:
        _ensure_storage()
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
