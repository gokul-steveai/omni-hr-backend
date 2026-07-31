import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.session import Base, get_db
from app.main import app
from app.models.role import Permission, Role
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_roles_test_db():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        perm_read = Permission(
            code="payroll:read", module="payroll", description="Read payroll"
        )
        perm_process = Permission(
            code="payroll:process", module="payroll", description="Process payroll"
        )
        session.add_all([perm_read, perm_process])
        await session.flush()

        admin_role = Role(
            name=UserRole.SUPER_ADMIN.value,
            description="Super Administrator",
            is_system=True,
            permissions=[perm_read, perm_process],
        )
        emp_role = Role(
            name=UserRole.EMPLOYEE.value,
            description="Standard Employee",
            is_system=True,
            permissions=[perm_read],
        )
        session.add_all([admin_role, emp_role])
        await session.flush()

        admin_user = User(
            email="admin@omnihr.com",
            password_hash=get_password_hash("AdminPass123!"),
            first_name="Admin",
            last_name="System",
            role_id=admin_role.id,
            is_active=True,
        )
        emp_user = User(
            email="employee@omnihr.com",
            password_hash=get_password_hash("EmpPass123!"),
            first_name="Employee",
            last_name="User",
            role_id=emp_role.id,
            is_active=True,
        )
        session.add_all([admin_user, emp_user])
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_permissions():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@omnihr.com", "password": "AdminPass123!"},
        )
        token = login_res.json()["data"]["access_token"]

        res = await ac.get(
            "/api/v1/permissions", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        permissions = res.json()
        assert len(permissions) >= 2


@pytest.mark.asyncio
async def test_create_and_delete_custom_role():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@omnihr.com", "password": "AdminPass123!"},
        )
        token = login_res.json()["data"]["access_token"]

        # Create custom role
        create_res = await ac.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Payroll Specialist",
                "description": "Custom role for payroll staff",
                "permission_ids": [],
            },
        )
        assert create_res.status_code == 201
        created_role = create_res.json()
        role_id = created_role["id"]
        assert created_role["name"] == "Payroll Specialist"
        assert created_role["is_system"] is False

        # Delete custom role
        del_res = await ac.delete(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_system_role_protection():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@omnihr.com", "password": "AdminPass123!"},
        )
        token = login_res.json()["data"]["access_token"]

        roles_res = await ac.get(
            "/api/v1/roles", headers={"Authorization": f"Bearer {token}"}
        )
        roles = roles_res.json()
        system_role = next(r for r in roles if r["name"] == "super_admin")

        # Attempt to delete system role
        del_res = await ac.delete(
            f"/api/v1/roles/{system_role['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 400
        body = del_res.json()
        assert body["error"]["code"] == "SYSTEM_ROLE_PROTECTED"
