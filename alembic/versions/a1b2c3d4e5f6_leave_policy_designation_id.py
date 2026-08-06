"""replace_role_id_with_designation_id_on_leave_accrual_policies

Revision ID: a1b2c3d4e5f6
Revises: 0e12ca119a30
Create Date: 2026-08-06 17:42:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0e12ca119a30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("leave_accrual_policies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("designation_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "leave_accrual_policies_designation_id_fkey",
            "designations",
            ["designation_id"],
            ["id"],
            ondelete="CASCADE",
        )
        # Drop legacy role_id if exists
        try:
            batch_op.drop_constraint(
                "leave_accrual_policies_role_id_fkey", type_="foreignkey"
            )
        except Exception:
            pass
        try:
            batch_op.drop_column("role_id")
        except Exception:
            pass


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("leave_accrual_policies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "leave_accrual_policies_role_id_fkey",
            "roles",
            ["role_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint(
            "leave_accrual_policies_designation_id_fkey", type_="foreignkey"
        )
        batch_op.drop_column("designation_id")
