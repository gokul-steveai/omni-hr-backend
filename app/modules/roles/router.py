import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.modules.roles.schemas import (
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    RoleWithPermissionsRead,
)
from app.modules.roles.service import RoleService
from app.schemas.common import MetaPayload, StandardResponse

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])
permissions_router = APIRouter(prefix="/permissions", tags=["Roles & Permissions"])


@router.get(
    "",
    response_model=StandardResponse[list[RoleRead]],
    dependencies=[Depends(require_permission("roles:read"))],
    response_model_exclude_none=True,
)
async def list_roles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = RoleService(db)
    roles, total = await service.list_roles(page=page, limit=limit, search=search)
    role_list = [RoleRead.model_validate(r) for r in roles]
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=role_list, meta=meta)


@permissions_router.get(
    "",
    response_model=StandardResponse[list[PermissionRead]],
    dependencies=[Depends(require_permission("roles:read"))],
    response_model_exclude_none=True,
)
async def list_permissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = RoleService(db)
    perms, total = await service.list_permissions(
        page=page, limit=limit, search=search, module=module
    )
    perm_list = [PermissionRead.model_validate(p) for p in perms]
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=perm_list, meta=meta)


@router.get(
    "/{role_id}/permissions",
    response_model=StandardResponse[list[PermissionRead]],
    dependencies=[Depends(require_permission("roles:read"))],
    response_model_exclude_none=True,
)
async def get_role_permissions(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RoleService(db)
    permissions = await service.get_role_permissions(role_id)
    perm_list = [PermissionRead.model_validate(p) for p in permissions]
    return StandardResponse.ok(data=perm_list)


@permissions_router.post(
    "",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("roles:write"))],
    response_model_exclude_none=True,
)
async def create_permission(
    perm_in: PermissionCreate,
    db: AsyncSession = Depends(get_db),
) -> PermissionRead:
    service = RoleService(db)
    return await service.create_permission(perm_in)


@router.post(
    "",
    response_model=RoleWithPermissionsRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("roles:write"))],
    response_model_exclude_none=True,
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
    dependencies=[Depends(require_permission("roles:read"))],
    response_model_exclude_none=True,
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
    dependencies=[Depends(require_permission("roles:write"))],
    response_model_exclude_none=True,
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
    dependencies=[Depends(require_permission("roles:delete"))],
    response_model_exclude_none=True,
)
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = RoleService(db)
    await service.delete_role(role_id)
