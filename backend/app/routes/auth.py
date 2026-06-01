from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserRead, TokenResponse
from app.services.auth_service import AuthService
from app.auth.dependencies import get_current_active_user
from app.auth.rbac import require_admin
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Register a new user. Admin only."""
    return AuthService(db).create_user(payload)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate and return JWT tokens."""
    return AuthService(db).authenticate(form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Issue a new access token from a valid refresh token."""
    return AuthService(db).refresh(refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_active_user)):
    """Return the authenticated user's profile."""
    return current_user
