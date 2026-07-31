import uuid
from typing import Optional

from fastapi import Depends, Query, status

from app.api.deps import (
    ProtectedAPIRouter,
    get_current_user,
    get_user_service,
    require_permission,
)
from app.models.role import PermissionEnum
from app.models.user import User
from app.modules.users.schemas import (
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserResponse,
)
from app.modules.users.service import UserService
from app.schemas.common import MetaPayload, StandardResponse

router = ProtectedAPIRouter()


@router.get(
    "",
    response_model=StandardResponse[list[UserResponse]],
    response_model_exclude_none=True,
)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    role_id: Optional[uuid.UUID] = Query(None),
    role_name: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(PermissionEnum.USERS_READ)),
    user_service: UserService = Depends(get_user_service),
):
    user_list, total = await user_service.list_users(
        page=page,
        limit=limit,
        search=search,
        department_id=department_id,
        role_id=role_id,
        role_name=role_name,
    )
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=user_list, meta=meta)


@router.post(
    "",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission(PermissionEnum.USERS_WRITE)),
    user_service: UserService = Depends(get_user_service),
):
    created_user = await user_service.create_user(payload, current_user)
    return StandardResponse.ok(data=created_user)


@router.get(
    "/me/profile",
    response_model=StandardResponse[ProfileResponse],
    response_model_exclude_none=True,
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    profile = await user_service.get_or_create_profile(current_user.id)
    return StandardResponse.ok(data=profile)


@router.put(
    "/me/profile",
    response_model=StandardResponse[ProfileResponse],
    response_model_exclude_none=True,
)
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    updated_profile = await user_service.update_profile(current_user.id, payload)
    return StandardResponse.ok(data=updated_profile)
