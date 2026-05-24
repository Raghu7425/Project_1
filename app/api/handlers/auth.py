from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.db.session import get_db
from app.repositories.users import UserRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    token = await AuthService(UserRepository(db)).register(body.email, body.password)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    token = await AuthService(UserRepository(db)).login(body.email, body.password)
    return TokenResponse(access_token=token)
