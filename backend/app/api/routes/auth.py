"""Authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Obtain a JWT access token",
    status_code=200,
)
def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Authenticate with email and password; receive a Bearer token."""
    result = AuthService(db).login(body.email, body.password)
    # Audit the login event
    AuditService(db).log(
        action=AuditAction.LOGIN,
        description=f"User {body.email} logged in",
        user_id=result.user.id,
    )
    return result


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user",
)
def get_me(current_user: CurrentUser) -> UserResponse:
    """Return profile data for the authenticated user."""
    return UserResponse.model_validate(current_user)
