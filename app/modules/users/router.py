import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.modules.users.schemas import (
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserResponse,
)
from app.modules.users.service import UserService
from app.schemas.common import MetaPayload, StandardResponse

router = APIRouter()


@router.get("", response_model=StandardResponse[list[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    role: Optional[UserRole] = Query(None),
    current_user: User = Depends(
        require_roles(
            [UserRole.SUPER_ADMIN, UserRole.HR_MANAGER, UserRole.DEPARTMENT_LEAD]
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    user_list, total = await user_service.list_users(
        page=page, limit=limit, search=search, department_id=department_id, role=role
    )
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=user_list, meta=meta)


@router.post(
    "",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(
        require_roles([UserRole.SUPER_ADMIN, UserRole.HR_MANAGER])
    ),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    created_user = await user_service.create_user(payload)
    return StandardResponse.ok(data=created_user)


@router.get("/me/profile", response_model=StandardResponse[ProfileResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    profile = await user_service.get_or_create_profile(current_user.id)
    return StandardResponse.ok(data=profile)


@router.put("/me/profile", response_model=StandardResponse[ProfileResponse])
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)
    updated_profile = await user_service.update_profile(current_user.id, payload)
    return StandardResponse.ok(data=updated_profile)
