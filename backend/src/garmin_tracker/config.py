from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Garmin Tracker"
    debug: bool = True

    # Auth
    secret_key: str = "change-me-in-production-use-openssl-rand"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    algorithm: str = "HS256"

    # Fernet key for encrypting Garmin session tokens
    token_encryption_key: str = ""

    # DynamoDB
    dynamodb_table: str = "garmin-tracker"
    dynamodb_endpoint: str = ""  # empty = real AWS; local e.g. http://127.0.0.1:8000
    aws_region: str = "us-west-2"

    # Optional S3 bucket for activity raw JSON
    data_bucket: str = ""

    # Sync transport: inline (local) or sqs (AWS worker)
    sync_backend: str = "inline"
    sync_queue_url: str = ""
    sync_chunk_days: int = 14

    # CloudFront → Function URL shared secret; empty disables the check (local)
    origin_secret: str = ""

    # App defaults
    default_timezone: str = "America/Denver"
    backfill_days: int = 365
    cors_origins: str = "http://localhost:5180,http://127.0.0.1:5180"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
