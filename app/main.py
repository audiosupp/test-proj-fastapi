"""
Точка входа FastAPI-приложения.

Запуск локально:
    uvicorn app.main:app --reload
"""

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.repositories.metrics_repository import LogRepository
from app.routers.contact_router import router as contact_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
log_repo = LogRepository()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Portfolio Contact API",
    description=(
        "Бэкенд портфолио разработчика с AI-анализом формы обратной связи. "
        "Использует файловое JSON-хранилище вместо базы данных."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — разрешаем запросы с любого источника
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Логирует каждый HTTP-запрос: метод, путь, статус, длительность."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    log_repo.log(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} duration={duration_ms:.1f}ms"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик необработанных исключений."""
    logger.exception("Необработанная ошибка: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера. Пожалуйста, попробуйте позже."},
    )


# Подключаем маршруты API
app.include_router(contact_router)

# Раздаём статические файлы (CSS/JS/изображения) из /static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_landing_page():
    """Отдаёт одностраничный фронтенд."""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)
