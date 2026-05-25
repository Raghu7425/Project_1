from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import JobStatus


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.:-]+$")
    payload: dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)
    idempotency_key: str | None = Field(default=None, max_length=128)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: JobStatus
    priority: int
    retry_count: int
    max_retries: int
    error_message: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class AdminStatsResponse(BaseModel):
    queued: int
    processing: int
    retrying: int
    completed: int
    failed: int
    dlq_size: int
