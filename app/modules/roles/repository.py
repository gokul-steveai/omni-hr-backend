import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, database_session: AsyncSession):
        super().__init__(Role, database_session)

    async def get_by_name(self, name: str) -> Optional[Role]:
        query_result = await self.database_session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )
        return query_result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        query_result = await self.database_session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        return query_result.scalar_one_or_none()

    async def list_roles(self) -> Sequence[Role]:
        query_result = await self.database_session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .order_by(Role.created_at.asc())
        )
        return query_result.scalars().all()

    async def list_permissions(self) -> Sequence[Permission]:
        query_result = await self.database_session.execute(
            select(Permission).order_by(Permission.module.asc(), Permission.code.asc())
        )
        return query_result.scalars().all()

    async def get_permission_by_code(self, code: str) -> Optional[Permission]:
        query_result = await self.database_session.execute(
            select(Permission).where(Permission.code == code)
        )
        return query_result.scalar_one_or_none()

    async def create_permission(self, permission: Permission) -> Permission:
        self.database_session.add(permission)
        await self.database_session.flush()
        return permission

    async def count_assigned_users(self, role_id: uuid.UUID) -> int:
        from sqlalchemy import func

        from app.models.user import User

        res = await self.database_session.execute(
            select(func.count(User.id)).where(User.role_id == role_id)
        )
        return res.scalar() or 0

    async def get_permissions_by_ids(
        self, permission_ids: list[uuid.UUID]
    ) -> Sequence[Permission]:
        if not permission_ids:
            return []
        query_result = await self.database_session.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        return query_result.scalars().all()
