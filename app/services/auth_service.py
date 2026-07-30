from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token, hash_token
from app.models.user import User, EmployeeProfile, RefreshToken
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.repositories.user_repository import UserRepository

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, payload: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email address or password."}
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "USER_DEACTIVATED", "message": "User account has been deactivated."}
            )

        return await self._issue_tokens(user)

    async def register_user(self, payload: RegisterRequest) -> TokenResponse:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email address already exists."}
            )

        new_user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=payload.role,
            is_active=True
        )
        await self.user_repo.create(new_user)
        
        # Instantiate profile
        profile = EmployeeProfile(user_id=new_user.id)
        self.db.add(profile)

        return await self._issue_tokens(new_user)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        decoded = decode_token(refresh_token, is_refresh=True)
        if not decoded:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired."}
            )

        hashed_rt = hash_token(refresh_token)
        db_token = await self.user_repo.get_refresh_token(hashed_rt)

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "REVOKED_REFRESH_TOKEN", "message": "Refresh token has been revoked or expired."}
            )

        token_exp = db_token.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        if token_exp < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "EXPIRED_REFRESH_TOKEN", "message": "Refresh token has expired."}
            )

        # Single-use revocation (rotation)
        db_token.is_revoked = True

        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "USER_INACTIVE", "message": "User account is inactive or deleted."}
            )

        return await self._issue_tokens(user)

    async def logout(self, user_id: str, refresh_token: str) -> None:
        hashed_rt = hash_token(refresh_token)
        db_token = await self.user_repo.get_refresh_token(hashed_rt)
        if db_token and str(db_token.user_id) == str(user_id):
            db_token.is_revoked = True
            await self.db.commit()

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(subject=str(user.id), roles=[user.role.value])
        refresh_token = create_refresh_token(subject=str(user.id))

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_revoked=False
        )
        await self.user_repo.save_refresh_token(db_token)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
