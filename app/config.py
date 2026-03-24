"""Application configuration management."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object populated from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "changeme"
    log_level: str = "INFO"
    debug: bool = False

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://loce:loce@localhost:5432/loce"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis / Celery ─────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Webhook HMAC Secrets ──────────────────────────────────
    webhook_hmac_secret_msg91: str = "changeme-msg91"
    webhook_hmac_secret_karix: str = "changeme-karix"
    webhook_hmac_secret_exotel: str = "changeme-exotel"
    webhook_hmac_secret_sendgrid: str = "changeme-sendgrid"
    webhook_hmac_secret_netcore: str = "changeme-netcore"

    # ── NBFC Adapters ─────────────────────────────────────────
    nbfc_a_base_url: str = "https://api.nbfc-a.example.com"
    nbfc_a_api_key: str = "changeme-nbfc-a"
    nbfc_b_base_url: str = "https://api.nbfc-b.example.com"
    nbfc_b_api_key: str = "changeme-nbfc-b"
    nbfc_c_base_url: str = "https://api.nbfc-c.example.com"
    nbfc_c_api_key: str = "changeme-nbfc-c"
    nbfc_default_timeout_seconds: int = 10
    nbfc_default_qps: int = 10

    # ── Communication Partners ────────────────────────────────
    msg91_auth_key: str = "changeme"
    karix_api_key: str = "changeme"
    karix_api_secret: str = "changeme"
    exotel_sid: str = "changeme"
    exotel_token: str = "changeme"
    sendgrid_api_key: str = "changeme"
    netcore_api_key: str = "changeme"

    # ── AWS / KMS ─────────────────────────────────────────────
    aws_region: str = "ap-south-1"
    aws_kms_key_arn: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # ── OpenTelemetry ─────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "loce"

    # ── Rate Limiter ──────────────────────────────────────────
    default_rate_limit_qps: int = 10
    default_rate_limit_burst: int = 20

    # ── JWT ───────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    def webhook_secret_for(self, partner: str) -> str:
        """Return the HMAC secret for a given partner name."""
        key = f"webhook_hmac_secret_{partner.lower()}"
        return getattr(self, key, "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
