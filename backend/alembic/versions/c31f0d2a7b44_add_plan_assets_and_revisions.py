"""add plan assets and revision history

Revision ID: c31f0d2a7b44
Revises: 9ce12ad2f8b1
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "c31f0d2a7b44"
down_revision: str | Sequence[str] | None = "9ce12ad2f8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "planasset",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("original_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("media_type", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("storage_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("uploaded_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_planasset_project_id"), "planasset", ["project_id"], unique=False)
    op.create_index(op.f("ix_planasset_sha256"), "planasset", ["sha256"], unique=False)

    op.create_table(
        "objectplan",
        sa.Column("project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("asset_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("current_revision_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("scale_m_per_px", sa.Float(), nullable=True),
        sa.Column("scale_status", sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
        sa.Column("review_status", sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
        sa.Column("provider_key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["planasset.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index(op.f("ix_objectplan_asset_id"), "objectplan", ["asset_id"], unique=False)
    op.create_index(
        op.f("ix_objectplan_current_revision_id"),
        "objectplan",
        ["current_revision_id"],
        unique=False,
    )

    op.create_table(
        "planrevision",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("asset_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
        sa.Column("review_status", sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
        sa.Column("provider_key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("created_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["planasset.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "revision_number"),
    )
    op.create_index(
        op.f("ix_planrevision_project_id"),
        "planrevision",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_planrevision_project_id"), table_name="planrevision")
    op.drop_table("planrevision")
    op.drop_index(op.f("ix_objectplan_current_revision_id"), table_name="objectplan")
    op.drop_index(op.f("ix_objectplan_asset_id"), table_name="objectplan")
    op.drop_table("objectplan")
    op.drop_index(op.f("ix_planasset_sha256"), table_name="planasset")
    op.drop_index(op.f("ix_planasset_project_id"), table_name="planasset")
    op.drop_table("planasset")

