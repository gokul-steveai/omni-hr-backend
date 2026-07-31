import uuid
from typing import Optional

from fastapi import Depends, Query, status

from app.api.deps import ProtectedAPIRouter, get_role_service, require_permission
from app.models.role import PermissionEnum
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

router = ProtectedAPIRouter(prefix="/roles", tags=["Roles & Permissions"])
permissions_router = ProtectedAPIRouter(
    prefix="/permissions", tags=["Roles & Permissions"]
)


@router.get(
    "",
    response_model=StandardResponse[list[RoleRead]],
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_READ))],
    response_model_exclude_none=True,
)
async def list_roles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role_service: RoleService = Depends(get_role_service),
):
    roles, total = await role_service.list_roles(page=page, limit=limit, search=search)
    role_list = [RoleRead.model_validate(r) for r in roles]
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=role_list, meta=meta)


@permissions_router.get(
    "",
    response_model=StandardResponse[list[PermissionRead]],
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_READ))],
    response_model_exclude_none=True,
)
async def list_permissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    role_service: RoleService = Depends(get_role_service),
):
    perms, total = await role_service.list_permissions(
        page=page, limit=limit, search=search, module=module
    )
    perm_list = [PermissionRead.model_validate(p) for p in perms]
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=perm_list, meta=meta)


@router.get(
    "/{role_id}/permissions",
    response_model=StandardResponse[list[PermissionRead]],
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_READ))],
    response_model_exclude_none=True,
)
async def get_role_permissions(
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
):
    permissions = await role_service.get_role_permissions(role_id)
    perm_list = [PermissionRead.model_validate(p) for p in permissions]
    return StandardResponse.ok(data=perm_list)


@permissions_router.post(
    "",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_WRITE))],
    response_model_exclude_none=True,
)
async def create_permission(
    perm_in: PermissionCreate,
    role_service: RoleService = Depends(get_role_service),
) -> PermissionRead:
    created_permission = await role_service.create_permission(perm_in)
    return PermissionRead.model_validate(created_permission)


@router.post(
    "",
    response_model=RoleWithPermissionsRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_WRITE))],
    response_model_exclude_none=True,
)
async def create_role(
    role_in: RoleCreate,
    role_service: RoleService = Depends(get_role_service),
) -> RoleWithPermissionsRead:
    created_role = await role_service.create_role(role_in)
    return RoleWithPermissionsRead.model_validate(created_role)


@router.get(
    "/{role_id}",
    response_model=RoleWithPermissionsRead,
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_READ))],
    response_model_exclude_none=True,
)
async def get_role(
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
) -> RoleWithPermissionsRead:
    role_entity = await role_service.get_role(role_id)
    return RoleWithPermissionsRead.model_validate(role_entity)


@router.put(
    "/{role_id}",
    response_model=RoleWithPermissionsRead,
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_WRITE))],
    response_model_exclude_none=True,
)
async def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdate,
    role_service: RoleService = Depends(get_role_service),
) -> RoleWithPermissionsRead:
    updated_role = await role_service.update_role(role_id, role_in)
    return RoleWithPermissionsRead.model_validate(updated_role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(PermissionEnum.ROLES_DELETE))],
    response_model_exclude_none=True,
)
async def delete_role(
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
) -> None:
    await role_service.delete_role(role_id)
