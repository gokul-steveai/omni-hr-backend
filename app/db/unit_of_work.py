from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.repository import UserRepository

class UnitOfWork:
    """
    Unit of Work Pattern to manage atomic database transactions
    and decouple Services from raw SQLAlchemy session handles.
    """
    def __init__(self, database_session: AsyncSession):
        self.database_session = database_session
        self.user_repository = UserRepository(database_session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        if exception_type is not None:
            await self.rollback_transaction()
        else:
            await self.commit_transaction()

    async def commit_transaction(self):
        await self.database_session.commit()

    async def rollback_transaction(self):
        await self.database_session.rollback()
