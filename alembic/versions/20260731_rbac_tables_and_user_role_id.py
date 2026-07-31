"""Add RBAC tables, backfill user role_id, and drop legacy role column

Revision ID: 20260731_rbac
Revises: 1397841f7b49
Create Date: 2026-07-31 12:00:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731_rbac"
down_revision: Union[str, None] = "1397841f7b49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    # 2. Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)
    op.create_index(
        op.f("ix_permissions_module"), "permissions", ["module"], unique=False
    )

    # 3. Create role_permissions junction table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # 4. Add role_id foreign key column to users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_role_id_roles", "roles", ["role_id"], ["id"], ondelete="RESTRICT"
        )

    # 5. Seed default system roles into roles table
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.UUID),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    now = datetime.now(timezone.utc)
    system_roles = {
        "super_admin": str(uuid.uuid4()),
        "hr_manager": str(uuid.uuid4()),
        "department_lead": str(uuid.uuid4()),
        "employee": str(uuid.uuid4()),
    }

    op.bulk_insert(
        roles_table,
        [
            {
                "id": system_roles["super_admin"],
                "name": "super_admin",
                "description": "Super Administrator with unrestricted access",
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": system_roles["hr_manager"],
                "name": "hr_manager",
                "description": "HR Manager with employee and payroll access",
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": system_roles["department_lead"],
                "name": "department_lead",
                "description": "Department Lead with team management access",
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": system_roles["employee"],
                "name": "employee",
                "description": "Standard Employee access",
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    # 6. Backfill existing users.role enum values to users.role_id
    connection = op.get_bind()
    for role_name, role_uuid in system_roles.items():
        connection.execute(
            sa.text(
                f"UPDATE users SET role_id = '{role_uuid}' WHERE role::text = '{role_name}' OR role::text = '{role_name.upper()}'"
            )
        )

    # Any remaining users default to employee role_id
    connection.execute(
        sa.text(
            f"UPDATE users SET role_id = '{system_roles['employee']}' WHERE role_id IS NULL"
        )
    )

    # 7. Drop legacy role column
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")


def downgrade() -> None:
    # 1. Re-add legacy role column to users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role", sa.String(length=50), nullable=True, server_default="employee"
            )
        )

    # 2. Backfill legacy role string from roles.name
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE users SET role = roles.name FROM roles WHERE users.role_id = roles.id"
        )
    )

    # 3. Drop foreign key and role_id column
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_role_id_roles", type_="foreignkey")
        batch_op.drop_column("role_id")

    # 4. Drop RBAC tables
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_permissions_module"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
