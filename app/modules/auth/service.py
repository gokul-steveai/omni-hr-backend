from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.services.password_service import PasswordService
from app.core.services.token_service import TokenService
from app.db.unit_of_work import UnitOfWork
from app.models.user import RefreshToken, User
from app.modules.auth.schemas import LoginRequest, TokenResponse


class AuthService:
    def __init__(self, database_session: AsyncSession):
        self.database_session = database_session
        self.password_service = PasswordService()
        self.token_service = TokenService()

    async def authenticate_user(self, payload: LoginRequest) -> TokenResponse:
        async with UnitOfWork(self.database_session) as unit_of_work:
            user_entity = await unit_of_work.user_repository.get_by_email(payload.email)
            if not user_entity or not self.password_service.verify_password(payload.password, user_entity.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email address or password."}
                )

            if not user_entity.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "USER_DEACTIVATED", "message": "User account has been deactivated."}
                )

            return await self._issue_tokens(user_entity, unit_of_work)

    async def refresh_tokens(self, refresh_token_string: str) -> TokenResponse:
        decoded_payload = self.token_service.decode_token(refresh_token_string, is_refresh=True)
        if not decoded_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired."}
            )

        hashed_refresh_token = self.token_service.hash_token(refresh_token_string)
        async with UnitOfWork(self.database_session) as unit_of_work:
            persisted_token = await unit_of_work.user_repository.get_refresh_token(hashed_refresh_token)

            if not persisted_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "REVOKED_REFRESH_TOKEN", "message": "Refresh token has been revoked or expired."}
                )

            expiration_datetime = persisted_token.expires_at
            if expiration_datetime.tzinfo is None:
                expiration_datetime = expiration_datetime.replace(tzinfo=timezone.utc)

            if expiration_datetime < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "EXPIRED_REFRESH_TOKEN", "message": "Refresh token has expired."}
                )

            persisted_token.is_revoked = True

            user_entity = await unit_of_work.user_repository.get_by_id(persisted_token.user_id)
            if not user_entity or not user_entity.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "USER_INACTIVE", "message": "User account is inactive or deleted."}
                )

            return await self._issue_tokens(user_entity, unit_of_work)

    async def logout(self, user_id_string: str, refresh_token_string: str) -> None:
        hashed_refresh_token = self.token_service.hash_token(refresh_token_string)
        async with UnitOfWork(self.database_session) as unit_of_work:
            persisted_token = await unit_of_work.user_repository.get_refresh_token(hashed_refresh_token)
            if persisted_token and str(persisted_token.user_id) == str(user_id_string):
                persisted_token.is_revoked = True

    async def _issue_tokens(self, user_entity: User, unit_of_work: UnitOfWork) -> TokenResponse:
        access_token_jwt = self.token_service.create_access_token(subject=str(user_entity.id), roles=[user_entity.role.value])
        refresh_token_jwt = self.token_service.create_refresh_token(subject=str(user_entity.id))

        token_record = RefreshToken(
            user_id=user_entity.id,
            token_hash=self.token_service.hash_token(refresh_token_jwt),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            is_revoked=False
        )
        await unit_of_work.user_repository.save_refresh_token(token_record)

        return TokenResponse(
            access_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
