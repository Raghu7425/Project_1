from fastapi import HTTPException, status

from app.repositories.users import UserRepository
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    async def register(self, email: str, password: str) -> str:
        if await self.users.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
        user = await self.users.create(email=email, password_hash=hash_password(password))
        return create_access_token(user.id)

    async def login(self, email: str, password: str) -> str:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        return create_access_token(user.id)
