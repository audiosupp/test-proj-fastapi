"""
Роутер для обратной связи (Controller layer).
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status, Depends

from app.repositories.metrics_repository import LogRepository, MetricsRepository, RateLimitRepository
from app.schemas.contact_schema import ContactCreate, ContactResponse, HealthResponse, MetricsResponse
from app.services.ai_service import AIService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Contact"])

# Провайдеры зависимостей (Dependency Injection)
def get_ai_service() -> AIService:
    return AIService()

def get_email_service() -> EmailService:
    return EmailService()

def get_metrics_repo() -> MetricsRepository:
    return MetricsRepository()

def get_log_repo() -> LogRepository:
    return LogRepository()

def get_rate_limit_repo() -> RateLimitRepository:
    from app.core.config import settings
    return RateLimitRepository(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )


def _client_ip(request: Request) -> str:
    """Определяет IP клиента с учётом reverse-proxy заголовков."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка здоровья",
    description="Возвращает статус сервиса — для мониторинга и Docker healthchecks.",
)
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Статистика обращений",
    description="Агрегированная статистика из файлового хранилища (без базы данных).",
)
async def get_metrics(
    metrics_repo: MetricsRepository = Depends(get_metrics_repo)
) -> MetricsResponse:
    data = metrics_repo.get_metrics()
    return MetricsResponse(**data)


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить форму обратной связи",
    description="Валидирует входные данные, запускает AI-анализ тональности, отправляет email и сохраняет метрики.",
    responses={
        429: {"description": "Превышен лимит запросов (Rate limit)"},
        422: {"description": "Ошибка валидации"},
    },
)
async def submit_contact(
    request: Request,
    payload: ContactCreate,
    ai_service: AIService = Depends(get_ai_service),
    email_service: EmailService = Depends(get_email_service),
    metrics_repo: MetricsRepository = Depends(get_metrics_repo),
    log_repo: LogRepository = Depends(get_log_repo),
    rate_limit_repo: RateLimitRepository = Depends(get_rate_limit_repo),
) -> ContactResponse:
    """
    POST /api/contact — основной эндпоинт для формы обратной связи.

    Порядок: rate limit → логирование → AI-анализ → email → метрики.
    """
    ip = _client_ip(request)

    allowed, retry_after = rate_limit_repo.is_allowed(ip)
    if not allowed:
        log_repo.log(f"RATE_LIMITED ip={ip} path=/api/contact")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много запросов. Попробуйте через {retry_after} секунд.",
            headers={"Retry-After": str(retry_after)},
        )

    log_repo.log(
        f"CONTACT ip={ip} email={payload.email} name={payload.name!r} "
        f"comment_len={len(payload.comment)}"
    )

    # Service layer — асинхронная цепочка вызовов
    analysis = await ai_service.analyze_comment(payload.comment)
    email_sent = await email_service.send_contact_notification(payload, analysis)

    if not email_sent:
        logger.warning("Не удалось отправить email для %s — продолжаем обновление метрик.", payload.email)

    metrics_repo.record_contact(analysis.sentiment, analysis.category)

    log_repo.log(
        f"CONTACT_OK ip={ip} sentiment={analysis.sentiment.value} category={analysis.category}"
    )

    return ContactResponse(
        message="Thank you! Your message has been received.",
        sentiment=analysis.sentiment,
        category=analysis.category,
    )
