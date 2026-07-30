import asyncio
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.organization import Department, Designation
from app.models.user import User, EmployeeProfile, UserRole
from app.models.leave import LeaveType, LeaveTypeEnum

async def seed_database():
    print("Initializing Database Tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("Seeding Departments & Designations...")
        # Departments
        depts_data = ["Engineering", "Human Resources", "Product & Design", "Sales & Marketing"]
        dept_map = {}
        for name in depts_data:
            res = await session.execute(select(Department).where(Department.name == name))
            dept = res.scalar_one_or_none()
            if not dept:
                dept = Department(name=name)
                session.add(dept)
                await session.flush()
            dept_map[name] = dept.id

        # Designations
        desigs_data = ["Senior Software Engineer", "HR Specialist", "Product Manager", "Account Executive"]
        desig_map = {}
        for title in desigs_data:
            res = await session.execute(select(Designation).where(Designation.title == title))
            desig = res.scalar_one_or_none()
            if not desig:
                desig = Designation(title=title)
                session.add(desig)
                await session.flush()
            desig_map[title] = desig.id

        # Leave Types
        leave_types = [
            (LeaveTypeEnum.CASUAL, 12.0, True, 1),
            (LeaveTypeEnum.SICK, 10.0, True, 1),
            (LeaveTypeEnum.EARNED, 15.0, True, 0),
            (LeaveTypeEnum.UNPAID, 30.0, True, 0)
        ]
        for lt_enum, default_quota, req_app, auto_app in leave_types:
            res = await session.execute(select(LeaveType).where(LeaveType.name == lt_enum))
            lt = res.scalar_one_or_none()
            if not lt:
                lt = LeaveType(name=lt_enum, default_quota=default_quota, requires_approval=req_app, auto_approve_threshold=auto_app)
                session.add(lt)

        await session.flush()

        print("Seeding Test User Accounts...")
        users_to_seed = [
            {
                "email": "admin@omnihr.com",
                "password": "AdminPass123!",
                "first_name": "Super",
                "last_name": "Admin",
                "role": UserRole.SUPER_ADMIN,
                "dept": "Engineering",
                "title": "Senior Software Engineer"
            },
            {
                "email": "hr@omnihr.com",
                "password": "HrPass123!",
                "first_name": "Sarah",
                "last_name": "Jenkins",
                "role": UserRole.HR_MANAGER,
                "dept": "Human Resources",
                "title": "HR Specialist"
            },
            {
                "email": "lead@omnihr.com",
                "password": "LeadPass123!",
                "first_name": "Michael",
                "last_name": "Scott",
                "role": UserRole.DEPARTMENT_LEAD,
                "dept": "Engineering",
                "title": "Senior Software Engineer"
            },
            {
                "email": "employee@omnihr.com",
                "password": "EmpPass123!",
                "first_name": "Jim",
                "last_name": "Halpert",
                "role": UserRole.EMPLOYEE,
                "dept": "Engineering",
                "title": "Senior Software Engineer"
            }
        ]

        created_users = {}
        for udata in users_to_seed:
            res = await session.execute(select(User).where(User.email == udata["email"]))
            user = res.scalar_one_or_none()
            if not user:
                user = User(
                    email=udata["email"],
                    password_hash=get_password_hash(udata["password"]),
                    first_name=udata["first_name"],
                    last_name=udata["last_name"],
                    role=udata["role"],
                    department_id=dept_map.get(udata["dept"]),
                    designation_id=desig_map.get(udata["title"]),
                    is_active=True
                )
                session.add(user)
                await session.flush()

                # Add profile
                profile = EmployeeProfile(user_id=user.id, phone_number="+1-555-0199", address="Scranton, PA")
                session.add(profile)

            created_users[udata["email"]] = user

        # Set Lead as Manager for Employee
        emp = created_users.get("employee@omnihr.com")
        lead = created_users.get("lead@omnihr.com")
        if emp and lead and not emp.manager_id:
            emp.manager_id = lead.id

        await session.commit()
        print("Database Seeding Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
