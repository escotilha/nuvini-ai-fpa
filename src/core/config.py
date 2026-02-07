"""
Configuration management using Pydantic settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_audit_bucket: str = "nuvini-fpa-audit-logs"
    s3_retention_years: int = 7

    # Claude API
    anthropic_api_key: str
    claude_model_default: str = "claude-sonnet-4-5"
    claude_model_critical: str = "claude-opus-4-6"
    claude_model_simple: str = "claude-haiku-4-5"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Security
    encryption_key_id: str
    jwt_secret_key: str
    session_secret: str

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    structured_logging: bool = True

    # BCB API
    bcb_api_url: str = "https://olinda.bcb.gov.br/olinda/service/PTAX/version/v1/odata/"

    # Environment
    environment: str = "development"
    debug: bool = False

    # Feature Flags
    feature_blockchain_audit: bool = False
    feature_realtime_consolidation: bool = False
    feature_ml_anomaly_detection: bool = False


# Global settings instance
settings = Settings()
