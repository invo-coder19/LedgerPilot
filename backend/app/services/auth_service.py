"""Authentication service."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginResponse, UserResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_repo = UserRepository(db)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Verify credentials and return the user if valid."""
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def login(self, email: str, password: str) -> LoginResponse:
        """Perform login and return a JWT access token."""
        user = self.authenticate(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = create_access_token(subject=str(user.id))
        return LoginResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
