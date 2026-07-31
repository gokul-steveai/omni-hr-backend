import uuid
from enum import Enum
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.services.cache_service import cache_service
from app.core.services.idempotency_service import (
    check_idempotency,
    idempotency_service,
)
from app.core.services.token_service import TokenService
from app.db.session import get_db
from app.models.role import PermissionEnum
from app.models.user import User, UserRole
from app.modules.auth.service import AuthService
from app.modules.roles.repository import RoleRepository
from app.modules.roles.service import RoleService
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

__all__ = [
    "get_db",
    "get_redis",
    "cache_service",
    "idempotency_service",
    "check_idempotency",
    "get_user_repository",
    "get_role_repository",
    "get_auth_service",
    "get_user_service",
    "get_role_service",
    "get_current_user",
    "require_roles",
    "require_permission",
    "ProtectedAPIRouter",
]

security_scheme = HTTPBearer()


# -----------------------------------------------------------------------------
# Dependency Injection Resolvers for Repositories and Domain Services
# -----------------------------------------------------------------------------


def get_user_repository(
    database_session: AsyncSession = Depends(get_db),
) -> UserRepository:
    return UserRepository(database_session)


def get_role_repository(
    database_session: AsyncSession = Depends(get_db),
) -> RoleRepository:
    return RoleRepository(database_session)


def get_auth_service(
    database_session: AsyncSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(
        database_session=database_session, user_repository=user_repository
    )


def get_user_service(
    database_session: AsyncSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
) -> UserService:
    return UserService(
        database_session=database_session,
        user_repository=user_repository,
        role_repository=role_repository,
    )


def get_role_service(
    database_session: AsyncSession = Depends(get_db),
    role_repository: RoleRepository = Depends(get_role_repository),
) -> RoleService:
    return RoleService(
        database_session=database_session, role_repository=role_repository
    )


# -----------------------------------------------------------------------------
# Authentication & Authorization Dependencies
# -----------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    token = credentials.credentials
    payload = TokenService.decode_token(token, is_refresh=False)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Access token is invalid or has expired.",
            },
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Token subject claim is missing.",
            },
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Malformed token subject UUID.",
            },
        ) from None

    user = await user_repository.get_with_details(user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "User account no longer exists.",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_DEACTIVATED", "message": "User account is inactive."},
        )

    return user


def require_roles(allowed_roles: list[UserRole | str]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        allowed_names = [
            r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles
        ]
        user_role_name = current_user.role.name if current_user.role else None

        if (
            user_role_name not in allowed_names
            and user_role_name != UserRole.SUPER_ADMIN.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": "User lacks required role to perform this action.",
                },
            )
        return current_user

    return role_checker


def require_permission(
    permission_code: PermissionEnum | str,
) -> Callable:
    target_code = (
        permission_code.value
        if isinstance(permission_code, Enum)
        else str(permission_code)
    )

    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role_name = current_user.role.name if current_user.role else None

        # Super admin always has full permissions
        if user_role_name == UserRole.SUPER_ADMIN.value:
            return current_user

        user_permissions = (
            [p.code for p in current_user.role.permissions]
            if current_user.role and current_user.role.permissions
            else []
        )

        if target_code not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"Required permission '{target_code}' is missing.",
                },
            )
        return current_user

    return permission_checker


# -----------------------------------------------------------------------------
# Reusable Protected Router Abstraction
# -----------------------------------------------------------------------------


class ProtectedAPIRouter(APIRouter):
    """
    APIRouter subclass that automatically appends Depends(get_current_user)
    to enforce token authentication across all registered endpoints.
    """

    def __init__(self, *args, dependencies: list | None = None, **kwargs):
        deps = list(dependencies) if dependencies else []
        deps.append(Depends(get_current_user))
        super().__init__(*args, dependencies=deps, **kwargs)
