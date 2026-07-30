import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole, EmployeeProfile

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
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

app.dependency_overrides[get_db] = override_get_db

async def run_verification():
    print("=== Module 1: Auth & RBAC Verification (Modular Feature Architecture) ===")
    
    # 1. Setup DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        admin = User(
            email="admin_test@omnihr.com",
            password_hash=get_password_hash("TestPass123!"),
            first_name="Admin",
            last_name="Tester",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        emp = User(
            email="emp_test@omnihr.com",
            password_hash=get_password_hash("EmpPass123!"),
            first_name="Employee",
            last_name="Tester",
            role=UserRole.EMPLOYEE,
            is_active=True
        )
        session.add_all([admin, emp])
        await session.flush()
        session.add(EmployeeProfile(user_id=admin.id, phone_number="1234567890"))
        session.add(EmployeeProfile(user_id=emp.id, phone_number="9876543210"))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test 1: Login Admin
        print("\n1. Testing POST /api/v1/auth/login (Admin)...")
        res1 = await ac.post("/api/v1/auth/login", json={"email": "admin_test@omnihr.com", "password": "TestPass123!"})
        assert res1.status_code == 200, f"Login failed: {res1.text}"
        admin_data = res1.json()["data"]
        admin_token = admin_data["access_token"]
        refresh_token = admin_data["refresh_token"]
        print("  ✓ Login Success! Access Token & Refresh Token Issued.")

        # Test 2: Get Current User Profile
        print("\n2. Testing GET /api/v1/auth/me...")
        res2 = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert res2.status_code == 200, f"Get me failed: {res2.text}"
        assert res2.json()["data"]["email"] == "admin_test@omnihr.com"
        print("  ✓ User Context Verified! Role:", res2.json()["data"]["role"])

        # Test 3: Token Refresh Rotation
        print("\n3. Testing POST /api/v1/auth/refresh (Rotation)...")
        res3 = await ac.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res3.status_code == 200, f"Refresh failed: {res3.text}"
        new_refresh_token = res3.json()["data"]["refresh_token"]
        print("  ✓ Refresh Token Rotated Successfully!")

        # Test 4: Reuse of Revoked Refresh Token must Fail
        print("\n4. Testing Reuse of Revoked Refresh Token (Security Check)...")
        res4 = await ac.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res4.status_code == 401, f"Expected 401 on revoked token, got: {res4.status_code}"
        print("  ✓ Revoked Refresh Token Re-use Blocked (401 Unauthorized)!")

        # Test 5: RBAC Authorization Check
        print("\n5. Testing RBAC Rules (Employee trying to access /api/v1/users)...")
        emp_login = await ac.post("/api/v1/auth/login", json={"email": "emp_test@omnihr.com", "password": "EmpPass123!"})
        emp_token = emp_login.json()["data"]["access_token"]
        
        res5 = await ac.get("/api/v1/users", headers={"Authorization": f"Bearer {emp_token}"})
        assert res5.status_code == 403, f"Expected 403 Forbidden, got: {res5.status_code}"
        assert res5.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
        print("  ✓ RBAC Enforced! Employee blocked with 403 Forbidden.")

        # Test 6: Self-Service Profile Update
        print("\n6. Testing PUT /api/v1/users/me/profile (Employee updating profile)...")
        res6 = await ac.put(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {emp_token}"},
            json={"phone_number": "+1-999-888-7777", "address": "Scranton, PA"}
        )
        assert res6.status_code == 200, f"Profile update failed: {res6.text}"
        assert res6.json()["data"]["phone_number"] == "+1-999-888-7777"
        print("  ✓ Self-Service Profile Updated Successfully!")

    print("\n=======================================================")
    print(" ALL MODULE 1 TESTS & SECURITY CHECKS PASSED CLEANLY! ")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
