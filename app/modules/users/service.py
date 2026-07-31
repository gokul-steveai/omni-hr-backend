import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import EmployeeProfile, User, UserRole
from app.modules.roles.repository import RoleRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserResponse,
)


class UserService:
    def __init__(
        self,
        database_session: AsyncSession,
        user_repository: UserRepository,
        role_repository: RoleRepository,
    ):
        self.database_session = database_session
        self.user_repo = user_repository
        self.role_repo = role_repository

    async def list_users(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        role_id: Optional[uuid.UUID] = None,
        role_name: Optional[str] = None,
    ) -> tuple[list[UserResponse], int]:
        offset = (page - 1) * limit
        users, total = await self.user_repo.search_users(
            offset=offset,
            limit=limit,
            search_term=search,
            department_id=department_id,
            role_id=role_id,
            role_name=role_name,
        )
        return [UserResponse.model_validate(u) for u in users], total

    async def create_user(
        self, payload: UserCreate, requesting_user: Optional[User] = None
    ) -> UserResponse:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EMAIL_ALREADY_EXISTS",
                    "message": "An account with this email address already exists.",
                },
            )

        role_id = payload.role_id
        if not role_id:
            default_role = await self.role_repo.get_by_name(UserRole.EMPLOYEE.value)
            if default_role:
                role_id = default_role.id
        else:
            target_role = await self.role_repo.get_with_permissions(role_id)
            if not target_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "ROLE_NOT_FOUND",
                        "message": "Target role for user creation does not exist.",
                    },
                )
            # Enforce actor-aware security policy
            if target_role.name == UserRole.SUPER_ADMIN.value:
                requester_role_name = (
                    requesting_user.role.name
                    if requesting_user and requesting_user.role
                    else None
                )
                if requester_role_name != UserRole.SUPER_ADMIN.value:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "ROLE_ASSIGNMENT_FORBIDDEN",
                            "message": "Only Super Administrators can assign the Super Admin role.",
                        },
                    )

        new_user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            role_id=role_id,
            department_id=payload.department_id,
            designation_id=payload.designation_id,
            manager_id=payload.manager_id,
            is_active=True,
        )
        await self.user_repo.create(new_user)

        profile = EmployeeProfile(user_id=new_user.id)
        self.database_session.add(profile)

        user_details = await self.user_repo.get_with_details(new_user.id)
        return UserResponse.model_validate(user_details)

    async def get_or_create_profile(self, user_id: uuid.UUID) -> ProfileResponse:
        profile = await self.user_repo.get_profile(user_id)
        if not profile:
            profile = EmployeeProfile(user_id=user_id)
            self.database_session.add(profile)

        profile_updated = await self.user_repo.get_profile(user_id)
        return ProfileResponse.model_validate(profile_updated)

    async def update_profile(
        self, user_id: uuid.UUID, payload: ProfileUpdate
    ) -> ProfileResponse:
        profile = await self.user_repo.get_profile(user_id)
        if not profile:
            profile = EmployeeProfile(user_id=user_id)
            self.database_session.add(profile)

        update_data = payload.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(profile, field, val)

        profile_updated = await self.user_repo.get_profile(user_id)
        return ProfileResponse.model_validate(profile_updated)
