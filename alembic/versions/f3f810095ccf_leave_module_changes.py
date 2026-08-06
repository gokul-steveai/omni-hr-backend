"""leave_module_changes

Revision ID: f3f810095ccf
Revises: 20260731_rbac
Create Date: 2026-08-06 16:51:36.526985

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3f810095ccf"
down_revision: Union[str, Sequence[str], None] = "20260731_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    accrualfrequency_enum = postgresql.ENUM(
        "MONTHLY",
        "QUARTERLY",
        "HALF_YEARLY",
        "YEARLY",
        "MANUAL",
        name="accrualfrequency",
    )
    accrualfrequency_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leave_accrual_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("leave_type_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=True),
        sa.Column(
            "frequency",
            accrualfrequency_enum,
            nullable=False,
        ),
        sa.Column("accrual_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("max_quota", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["leave_type_id"], ["leave_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("leave_allocations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_accrual_date", sa.Date(), nullable=True))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("users_role_id_fkey"), type_="foreignkey")
        batch_op.create_foreign_key(
            None, "roles", ["role_id"], ["id"], ondelete="RESTRICT"
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("leave_accrual_policies")

    accrualfrequency_enum = postgresql.ENUM(
        "MONTHLY",
        "QUARTERLY",
        "HALF_YEARLY",
        "YEARLY",
        "MANUAL",
        name="accrualfrequency",
    )
    accrualfrequency_enum.drop(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("users_role_id_fkey"),
            "roles",
            ["role_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("leave_allocations", schema=None) as batch_op:
        batch_op.drop_column("last_accrual_date")
