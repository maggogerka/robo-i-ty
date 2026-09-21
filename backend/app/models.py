from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=320)
    password_hash: str
    role: str = Field(default="user", index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=now_utc)


class ObjectType(SQLModel, table=True):
    code: str = Field(primary_key=True, max_length=50)
    name: str
    readiness: str


class ObjectParameterDefinition(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("object_type_code", "code"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    object_type_code: str = Field(foreign_key="objecttype.code", index=True)
    code: str = Field(index=True)
    name: str
    section: str
    unit: str | None = None
    baseline: Any = Field(default=None, sa_column=Column(JSON))
    minimum: float | None = None
    maximum: float | None = None
    required: bool = False
    value_type: str = "number"
    note: str | None = Field(default=None, sa_column=Column(Text))
    source_status: str = "source_present"
    source_name: str | None = None


class Project(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    name: str
    object_type_code: str = Field(foreign_key="objecttype.code")
    calculation_version: str = "2026.09.1"
    is_demo: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ProjectParameterValue(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("project_id", "definition_code"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    definition_code: str = Field(index=True)
    value: Any = Field(sa_column=Column(JSON))
    original_value: Any = Field(default=None, sa_column=Column(JSON))
    source_status: str = "source_present"
    source_comment: str | None = None
    changed_by: str | None = Field(default=None, foreign_key="user.id")
    changed_at: datetime | None = None


class RobotSolution(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    manufacturer: str = Field(index=True)
    catalog_type: str | None = Field(default=None, index=True)
    subtype: str | None = None
    status: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    process: str | None = Field(default=None, index=True)
    trl: int | None = None
    market_potential: float | None = None
    region: str | None = None
    industry: str | None = Field(default=None, index=True)
    price_rub: float | None = None
    max_payload_kg: float | None = None
    data_completeness: float = 0
    source_status: str = "source_present"
    source_name: str
    source_date: str | None = None


class SourceEvidence(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    title: str
    source_type: str
    source_name: str
    source_url: str | None = None
    source_date: str | None = None
    status: str = "source_present"


class DeploymentCase(SQLModel, table=True):
    id: str = Field(primary_key=True)
    solution_id: str = Field(foreign_key="robotsolution.id", index=True)
    summary: str = Field(sa_column=Column(Text))
    source_name: str


class MatchingRun(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    model_version: str = "2026.09.1"
    input_snapshot: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class MatchingCandidate(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    matching_run_id: str = Field(foreign_key="matchingrun.id", index=True)
    solution_id: str = Field(foreign_key="robotsolution.id")
    rank: int
    score: float
    eligible: bool
    explanation: dict[str, Any] = Field(sa_column=Column(JSON))


class EconomicScenario(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    scenario_type: str
    model_version: str = "2026.09.2"
    created_at: datetime = Field(default_factory=now_utc)


class EconomicAssumption(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    scenario_id: str = Field(foreign_key="economicscenario.id", index=True)
    key: str
    original_value: Any = Field(sa_column=Column(JSON))
    current_value: Any = Field(sa_column=Column(JSON))
    unit: str | None = None
    status: str = "assumed"
    changed_by: str | None = None
    changed_at: datetime | None = None


class EconomicResult(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    scenario_id: str = Field(foreign_key="economicscenario.id", index=True)
    metrics: dict[str, Any] = Field(sa_column=Column(JSON))


class Plan(SQLModel, table=True):
    project_id: str = Field(foreign_key="project.id", primary_key=True)
    name: str = "Основной план"
    width_m: float
    height_m: float
    revision: int = 1
    source_status: str = "assumed"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class PlanElement(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("plan_project_id", "element_key"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    plan_project_id: str = Field(foreign_key="plan.project_id", index=True)
    element_key: str = Field(max_length=64)
    kind: str = Field(index=True, max_length=32)
    label: str = Field(max_length=120)
    x_m: float
    y_m: float
    width_m: float
    height_m: float
    rotation_deg: float = 0
    properties: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class SimulationRun(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    plan_revision: int
    model_version: str = "2026.09.1"
    input_snapshot: dict[str, Any] = Field(sa_column=Column(JSON))
    result_snapshot: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class SimulationMetric(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    simulation_run_id: str = Field(foreign_key="simulationrun.id", index=True)
    key: str = Field(max_length=80)
    value: float
    unit: str = Field(max_length=32)
    status: str = "assumed"


class AuditEvent(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    actor_id: str | None = Field(default=None, foreign_key="user.id")
    action: str = Field(index=True)
    entity_type: str
    entity_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)
