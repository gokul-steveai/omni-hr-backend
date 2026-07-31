import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role
from app.modules.roles.repository import RoleRepository
from app.modules.roles.schemas import RoleCreate, RoleUpdate


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = RoleRepository(db)

    async def list_roles(self) -> Sequence[Role]:
        return await self.role_repo.list_roles()

    async def list_permissions(self) -> Sequence[Permission]:
        return await self.role_repo.list_permissions()

    async def get_role(self, role_id: uuid.UUID) -> Role:
        role = await self.role_repo.get_with_permissions(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ROLE_NOT_FOUND", "message": "Role not found."},
            )
        return role

    async def create_role(self, role_in: RoleCreate) -> Role:
        existing_role = await self.role_repo.get_by_name(role_in.name)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ROLE_ALREADY_EXISTS",
                    "message": f"A role with name '{role_in.name}' already exists.",
                },
            )

        permissions = []
        if role_in.permission_ids:
            permissions = list(
                await self.role_repo.get_permissions_by_ids(role_in.permission_ids)
            )

        role = Role(
            name=role_in.name,
            description=role_in.description,
            is_system=False,
            permissions=permissions,
        )
        await self.role_repo.create(role)
        return role

    async def update_role(self, role_id: uuid.UUID, role_in: RoleUpdate) -> Role:
        role = await self.get_role(role_id)

        if role_in.name and role_in.name != role.name:
            if role.is_system:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "SYSTEM_ROLE_PROTECTED",
                        "message": "Cannot rename a system role.",
                    },
                )
            existing_role = await self.role_repo.get_by_name(role_in.name)
            if existing_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "ROLE_ALREADY_EXISTS",
                        "message": f"A role with name '{role_in.name}' already exists.",
                    },
                )
            role.name = role_in.name

        if role_in.description is not None:
            role.description = role_in.description

        if role_in.permission_ids is not None:
            permissions = list(
                await self.role_repo.get_permissions_by_ids(role_in.permission_ids)
            )
            role.permissions = permissions

        await self.db.flush()
        return role

    async def delete_role(self, role_id: uuid.UUID) -> None:
        role = await self.get_role(role_id)
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SYSTEM_ROLE_PROTECTED",
                    "message": "System roles cannot be deleted.",
                },
            )

        # Check if users are assigned
        assigned_user_count = await self.role_repo.count_assigned_users(role_id)
        if assigned_user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ROLE_IN_USE",
                    "message": "Cannot delete role while users are assigned to it.",
                },
            )

        await self.role_repo.delete(role)
