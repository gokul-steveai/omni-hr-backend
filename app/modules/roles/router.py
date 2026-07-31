import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import UserRole
from app.modules.roles.schemas import (
    PermissionRead,
    RoleCreate,
    RoleUpdate,
    RoleWithPermissionsRead,
)
from app.modules.roles.service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])
permissions_router = APIRouter(prefix="/permissions", tags=["Roles & Permissions"])


@router.get(
    "",
    response_model=list[RoleWithPermissionsRead],
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.HR_MANAGER]))],
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
) -> Sequence[RoleWithPermissionsRead]:
    service = RoleService(db)
    return await service.list_roles()


@permissions_router.get(
    "",
    response_model=list[PermissionRead],
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.HR_MANAGER]))],
)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
) -> Sequence[PermissionRead]:
    service = RoleService(db)
    return await service.list_permissions()


@router.post(
    "",
    response_model=RoleWithPermissionsRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN]))],
)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
) -> RoleWithPermissionsRead:
    service = RoleService(db)
    return await service.create_role(role_in)


@router.get(
    "/{role_id}",
    response_model=RoleWithPermissionsRead,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.HR_MANAGER]))],
)
async def get_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RoleWithPermissionsRead:
    service = RoleService(db)
    return await service.get_role(role_id)


@router.put(
    "/{role_id}",
    response_model=RoleWithPermissionsRead,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN]))],
)
async def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> RoleWithPermissionsRead:
    service = RoleService(db)
    return await service.update_role(role_id, role_in)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN]))],
)
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = RoleService(db)
    await service.delete_role(role_id)
