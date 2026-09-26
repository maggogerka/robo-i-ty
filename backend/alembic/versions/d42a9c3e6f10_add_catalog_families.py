"""add catalog families and configurations

Revision ID: d42a9c3e6f10
Revises: c31f0d2a7b44
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "d42a9c3e6f10"
down_revision: str | Sequence[str] | None = "c31f0d2a7b44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "robotfamily",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("manufacturer", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_robotfamily_name"), "robotfamily", ["name"], unique=False)
    op.create_index(
        op.f("ix_robotfamily_manufacturer"), "robotfamily", ["manufacturer"], unique=False
    )
    op.add_column(
        "robotsolution",
        sa.Column("family_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "robotsolution",
        sa.Column("source_product_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "robotsolution",
        sa.Column("configuration_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column("robotsolution", sa.Column("width_m", sa.Float(), nullable=True))
    op.add_column("robotsolution", sa.Column("length_m", sa.Float(), nullable=True))
    op.add_column("robotsolution", sa.Column("turning_radius_m", sa.Float(), nullable=True))
    op.add_column("robotsolution", sa.Column("attributes", sa.JSON(), nullable=True))
    op.add_column("robotsolution", sa.Column("source_row_number", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_robotsolution_family_id_robotfamily",
        "robotsolution",
        "robotfamily",
        ["family_id"],
        ["id"],
    )
    for column in ("family_id", "source_product_id", "configuration_key"):
        op.create_index(op.f(f"ix_robotsolution_{column}"), "robotsolution", [column])


def downgrade() -> None:
    for column in ("configuration_key", "source_product_id", "family_id"):
        op.drop_index(op.f(f"ix_robotsolution_{column}"), table_name="robotsolution")
    op.drop_constraint(
        "fk_robotsolution_family_id_robotfamily", "robotsolution", type_="foreignkey"
    )
    for column in (
        "source_row_number",
        "attributes",
        "turning_radius_m",
        "length_m",
        "width_m",
        "configuration_key",
        "source_product_id",
        "family_id",
    ):
        op.drop_column("robotsolution", column)
    op.drop_index(op.f("ix_robotfamily_manufacturer"), table_name="robotfamily")
    op.drop_index(op.f("ix_robotfamily_name"), table_name="robotfamily")
    op.drop_table("robotfamily")
