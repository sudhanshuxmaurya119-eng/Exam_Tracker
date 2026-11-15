"""FastAPI Production Entrypoint for the Examination Seating Plan Portal."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import time
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import auth, datasets, examinations, imports, maintenance, search
from app.core import database
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.security import hash_password
from app.models.models import AdminUser
from app.schemas.schemas import HealthResponse
from app.services.storage_service import storage_service

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def bootstrap_initial_admin() -> None:
    """Create the initial super_admin account if configured via environment variables and no admin exists."""
    init_password = settings.INITIAL_ADMIN_PASSWORD.strip()
    if not init_password:
        return

    with database.SessionLocal() as db:
        count = db.scalar(select(func.count(AdminUser.id))) or 0
        if count == 0:
            admin = AdminUser(
                username=settings.INITIAL_ADMIN_USERNAME.strip(),
                email=settings.INITIAL_ADMIN_EMAIL.strip().lower(),
                full_name=settings.INITIAL_ADMIN_FULL_NAME.strip(),
                hashed_password=hash_password(init_password),
                role="super_admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(
                "Bootstrapped initial super_admin account '%s' (%s)",
                admin.username,
                admin.email,
            )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle manager."""
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )
    try:
        database.Base.metadata.create_all(bind=database.engine)
        bootstrap_initial_admin()
        storage_service.ensure_bucket_exists()
    except Exception as exc:
        logger.error("Startup initialization warning/error: %s", exc)
        if settings.APP_ENV.lower() == "production":
            raise
    yield
    logger.info("Shutting down %s", settings.APP_NAME)
    database.engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production Backend API for Examination Seating Plan Finder with "
        "Supabase PostgreSQL, Private Supabase Storage ('seating-datasets'), "
        "Transactional Excel Import Pipeline, and Fast Roll-Number Search."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Secure CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition", "X-Process-Time-Ms"],
)


@app.middleware("http")
async def security_and_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# =============================================================================
# Global Structured Exception Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    formatted_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(p) for p in err.get("loc", []))
        formatted_errors.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "detail": "Request validation failed: " + "; ".join(formatted_errors),
            "validation_errors": formatted_errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "A database error occurred while processing your request.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An unexpected internal server error occurred.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# =============================================================================
# Health Check Endpoints (GET /health and GET /api/v1/health)
# =============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Verify backend availability, PostgreSQL connectivity, and storage status",
)
@app.get(
    f"{settings.API_V1_PREFIX}/health",
    response_model=HealthResponse,
    tags=["Health"],
    include_in_schema=False,
)
def health_check() -> JSONResponse:
    db_status = database.verify_database_connection()
    storage_status = storage_service.get_storage_health()

    is_healthy = bool(db_status.get("connected"))
    overall_status = "healthy" if is_healthy else "unhealthy"
    http_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = HealthResponse(
        status=overall_status,
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        storage=storage_status,
    )
    return JSONResponse(
        status_code=http_code,
        content=payload.model_dump(mode="json"),
    )


# =============================================================================
# API v1 Routers
# =============================================================================

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(examinations.router, prefix=settings.API_V1_PREFIX)
app.include_router(imports.router, prefix=settings.API_V1_PREFIX)
app.include_router(datasets.router, prefix=settings.API_V1_PREFIX)
app.include_router(search.router, prefix=settings.API_V1_PREFIX)
app.include_router(maintenance.router, prefix=settings.API_V1_PREFIX)
