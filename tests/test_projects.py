import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import Base, engine
from app.main import app


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_multi_department_projects_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Login as Admin
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@omni-hr.com", "password": "Password123!"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Create Company-Wide Project (Empty department_ids)
        res_global = await client.post(
            "/api/v1/projects",
            json={"name": "Global All-Hands", "code": "GLOB-01", "department_ids": []},
            headers=admin_headers,
        )
        assert res_global.status_code == 201
        data_global = res_global.json()["data"]
        assert data_global["departments"] == []

        # 3. Create Department Bounded Project with non-existent ID
        dummy_dept_id = str(uuid.uuid4())
        res_invalid = await client.post(
            "/api/v1/projects",
            json={
                "name": "Invalid Dept Project",
                "code": "BAD-01",
                "department_ids": [dummy_dept_id],
            },
            headers=admin_headers,
        )
        # Should return 400 because dummy department ID doesn't exist
        assert res_invalid.status_code == 400

        # 4. List projects
        res_list = await client.get("/api/v1/projects", headers=admin_headers)
        assert res_list.status_code == 200
        projects = res_list.json()["data"]
        assert any(p["code"] == "GLOB-01" for p in projects)
