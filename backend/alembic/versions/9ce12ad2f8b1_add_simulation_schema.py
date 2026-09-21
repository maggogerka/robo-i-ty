"""add simulation schema

Revision ID: 9ce12ad2f8b1
Revises: b4f97bd5883c
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "9ce12ad2f8b1"
down_revision: str | Sequence[str] | None = "b4f97bd5883c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan",
        sa.Column("project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_table(
        "planelement",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("plan_project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("element_key", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("x_m", sa.Float(), nullable=False),
        sa.Column("y_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("rotation_deg", sa.Float(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["plan_project_id"], ["plan.project_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_project_id", "element_key"),
    )
    op.create_index(op.f("ix_planelement_kind"), "planelement", ["kind"], unique=False)
    op.create_index(
        op.f("ix_planelement_plan_project_id"),
        "planelement",
        ["plan_project_id"],
        unique=False,
    )
    op.create_table(
        "simulationrun",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("project_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("plan_revision", sa.Integer(), nullable=False),
        sa.Column("model_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=True),
        sa.Column("result_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulationrun_project_id"),
        "simulationrun",
        ["project_id"],
        unique=False,
    )
    op.create_table(
        "simulationmetric",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("simulation_run_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulationrun.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulationmetric_simulation_run_id"),
        "simulationmetric",
        ["simulation_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_simulationmetric_simulation_run_id"),
        table_name="simulationmetric",
    )
    op.drop_table("simulationmetric")
    op.drop_index(op.f("ix_simulationrun_project_id"), table_name="simulationrun")
    op.drop_table("simulationrun")
    op.drop_index(op.f("ix_planelement_plan_project_id"), table_name="planelement")
    op.drop_index(op.f("ix_planelement_kind"), table_name="planelement")
    op.drop_table("planelement")
    op.drop_table("plan")
