"""Application configuration and environment variable validation."""

import os
from functools import lru_cache
from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production and development configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Metadata
    APP_NAME: str = "Examination Seating Plan Portal API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"  # development | testing | production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Database Configuration (Supabase PostgreSQL primary database)
    # In production, MUST be a PostgreSQL URL (sqlite is strictly forbidden).
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/exam_seating_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300
    DB_ECHO: bool = False

    # Supabase Storage Configuration (Private Bucket: seating-datasets)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "seating-datasets"
    SIGNED_URL_EXPIRES_SECONDS: int = 300

    # JWT & Authentication Configuration
    JWT_SECRET_KEY: str = "change-this-in-production-to-a-strong-64-char-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Initial Administrator Bootstrap (Optional via env vars)
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_EMAIL: str = "admin@examportal.edu"
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_FULL_NAME: str = "Chief Examination Controller"

    # CORS & Frontend Origins
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Upload & Rate Limit Policies
    MAX_UPLOAD_SIZE_MB: int = 10
    RATE_LIMIT_SEARCH_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 120

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not v:
            return v
        v = v.strip()
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and "+psycopg" not in v:
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    @model_validator(mode="after")
    def enforce_production_constraints(self) -> "Settings":
        env = self.APP_ENV.lower().strip()
        if env == "production":
            if not self.DATABASE_URL or self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "CRITICAL: SQLite is prohibited in production. "
                    "Configure DATABASE_URL with your Supabase PostgreSQL connection string."
                )
            if (
                not self.JWT_SECRET_KEY
                or self.JWT_SECRET_KEY == "change-this-in-production-to-a-strong-64-char-random-secret"
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "CRITICAL: JWT_SECRET_KEY must be set to a strong secret (>= 32 chars) in production."
                )
            if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError(
                    "CRITICAL: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production "
                    "for private storage bucket 'seating-datasets'."
                )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.FRONTEND_URL:
            fe = self.FRONTEND_URL.strip().rstrip("/")
            if fe and fe not in origins:
                origins.append(fe)
        return origins

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
