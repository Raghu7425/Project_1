from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Distributed Task Queue Platform"
    environment: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = Field(
        default="postgresql+asyncpg://jobs:jobs@postgres:5432/jobs",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", validation_alias="REDIS_URL")
    jwt_secret: str = Field(default="change-me-in-production", validation_alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60
    rate_limit_per_minute: int = 60
    worker_concurrency: int = 4
    worker_shutdown_grace_seconds: int = 30
    job_timeout_seconds: int = 120
    stalled_job_grace_seconds: int = 60
    default_max_retries: int = 3
    redis_stream_prefix: str = "jobs"
    consumer_group: str = "job-workers"
    upload_dir: str = "storage/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
