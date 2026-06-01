from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user import UserCreate, TokenResponse
from app.auth.jwt import create_access_token, create_refresh_token, decode_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def _build_tokens(self, user: User) -> TokenResponse:
        data = {"sub": str(user.id), "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(data),
            refresh_token=create_refresh_token(data),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def create_user(self, payload: UserCreate) -> User:
        if self.db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=self._hash_password(payload.password),
            role=payload.role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> TokenResponse:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self._verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        return self._build_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user = self.db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return self._build_tokens(user)
