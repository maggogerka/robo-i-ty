from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    AuditEvent,
    Plan,
    PlanElement,
    Project,
    ProjectParameterValue,
    SimulationMetric,
    SimulationRun,
    User,
)
from ..schemas import PlanElementPayload, PlanPayload, SimulationRequest
from ..security import get_current_user
from ..simulation import (
    SIMULATION_MODEL_VERSION,
    Point,
    Rect,
    SimulationInputs,
    build_route,
    calculate_simulation,
)

router = APIRouter(prefix="/projects", tags=["2D-симуляция"])


def _project(project_id: str, user: User, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None or (project.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


def _default_plan() -> PlanPayload:
    return PlanPayload(
        name="Демо-план склада",
        width_m=60,
        height_m=36,
        elements=[
            PlanElementPayload(
                id="pickup-1",
                kind="pickup",
                label="Приёмка",
                x_m=3,
                y_m=14,
                width_m=8,
                height_m=8,
            ),
            PlanElementPayload(
                id="storage-1",
                kind="storage",
                label="Стеллаж A",
                x_m=18,
                y_m=3,
                width_m=8,
                height_m=13,
            ),
            PlanElementPayload(
                id="storage-2",
                kind="storage",
                label="Стеллаж B",
                x_m=31,
                y_m=3,
                width_m=8,
                height_m=13,
            ),
            PlanElementPayload(
                id="storage-3",
                kind="storage",
                label="Стеллаж C",
                x_m=18,
                y_m=21,
                width_m=8,
                height_m=12,
            ),
            PlanElementPayload(
                id="storage-4",
                kind="storage",
                label="Стеллаж D",
                x_m=31,
                y_m=21,
                width_m=8,
                height_m=12,
            ),
            PlanElementPayload(
                id="dropoff-1",
                kind="dropoff",
                label="Отгрузка",
                x_m=49,
                y_m=14,
                width_m=8,
                height_m=8,
            ),
            PlanElementPayload(
                id="charger-1",
                kind="charger",
                label="Зарядка",
                x_m=48,
                y_m=4,
                width_m=7,
                height_m=5,
            ),
        ],
    )


def _plan_payload(plan: Plan, session: Session) -> dict[str, Any]:
    elements = list(
        session.exec(
            select(PlanElement)
            .where(PlanElement.plan_project_id == plan.project_id)
            .order_by(PlanElement.kind, PlanElement.label)
        )
    )
    return {
        "name": plan.name,
        "width_m": plan.width_m,
        "height_m": plan.height_m,
        "revision": plan.revision,
        "source_status": plan.source_status,
        "elements": [
            {
                "id": item.element_key,
                "kind": item.kind,
                "label": item.label,
                "x_m": item.x_m,
                "y_m": item.y_m,
                "width_m": item.width_m,
                "height_m": item.height_m,
                "rotation_deg": item.rotation_deg,
            }
            for item in elements
        ],
    }


def _saved_or_default(project_id: str, session: Session) -> tuple[dict[str, Any], int]:
    saved = session.get(Plan, project_id)
    if saved:
        return _plan_payload(saved, session), saved.revision
    default = _default_plan().model_dump()
    default.update({"revision": 0, "source_status": "assumed"})
    return default, 0


def _center(item: dict[str, Any]) -> Point:
    return Point(
        float(item["x_m"]) + float(item["width_m"]) / 2,
        float(item["y_m"]) + float(item["height_m"]) / 2,
    )


@router.get("/{project_id}/plan")
def get_plan(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _project(project_id, user, session)
    payload, _ = _saved_or_default(project_id, session)
    return payload


@router.put("/{project_id}/plan")
def save_plan(
    project_id: str,
    payload: PlanPayload,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _project(project_id, user, session)
    plan = session.get(Plan, project_id)
    now = datetime.now(UTC)
    if plan is None:
        plan = Plan(
            project_id=project_id,
            name=payload.name,
            width_m=payload.width_m,
            height_m=payload.height_m,
        )
    else:
        plan.name = payload.name
        plan.width_m = payload.width_m
        plan.height_m = payload.height_m
        plan.revision += 1
        plan.updated_at = now
    session.add(plan)
    for item in session.exec(select(PlanElement).where(PlanElement.plan_project_id == project_id)):
        session.delete(item)
    session.flush()
    for item in payload.elements:
        session.add(
            PlanElement(
                element_key=item.id,
                plan_project_id=project_id,
                kind=item.kind,
                label=item.label,
                x_m=item.x_m,
                y_m=item.y_m,
                width_m=item.width_m,
                height_m=item.height_m,
                rotation_deg=item.rotation_deg,
            )
        )
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="project.plan.save",
            entity_type="Plan",
            entity_id=project_id,
            details={"revision": plan.revision, "element_count": len(payload.elements)},
        )
    )
    session.commit()
    session.refresh(plan)
    return _plan_payload(plan, session)


@router.post("/{project_id}/simulation")
def run_simulation(
    project_id: str,
    payload: SimulationRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _project(project_id, user, session)
    plan_payload, revision = _saved_or_default(project_id, session)
    elements = plan_payload["elements"]
    pickup = next(item for item in elements if item["kind"] == "pickup")
    dropoff = next(item for item in elements if item["kind"] == "dropoff")
    obstacles = [
        Rect(item["x_m"], item["y_m"], item["width_m"], item["height_m"])
        for item in elements
        if item["kind"] in {"storage", "obstacle"}
    ]
    route, route_warnings = build_route(_center(pickup), _center(dropoff), obstacles)
    values = {
        item.definition_code: item.value
        for item in session.exec(
            select(ProjectParameterValue).where(ProjectParameterValue.project_id == project_id)
        )
    }
    daily_tasks = values.get("daily_tasks")
    shift_hours = values.get("shift_hours")
    shifts_per_day = values.get("shifts_per_day")
    assumptions: list[dict[str, Any]] = []
    if not isinstance(daily_tasks, int | float) or daily_tasks <= 0:
        daily_tasks = 1_000
        assumptions.append(
            {
                "key": "daily_tasks",
                "value": daily_tasks,
                "unit": "заданий/сутки",
                "status": "assumed",
            }
        )
    if not isinstance(shift_hours, int | float) or shift_hours <= 0:
        shift_hours = 8
        assumptions.append(
            {
                "key": "shift_hours",
                "value": shift_hours,
                "unit": "ч/смену",
                "status": "assumed",
            }
        )
    if not isinstance(shifts_per_day, int | float) or shifts_per_day <= 0:
        shifts_per_day = 2
        assumptions.append(
            {
                "key": "shifts_per_day",
                "value": shifts_per_day,
                "unit": "смен/сутки",
                "status": "assumed",
            }
        )
    assumptions.extend(
        [
            {
                "key": "robot_speed_m_s",
                "value": payload.robot_speed_m_s,
                "unit": "м/с",
                "status": "assumed",
            },
            {
                "key": "handling_time_seconds",
                "value": payload.handling_time_seconds,
                "unit": "с/операцию",
                "status": "assumed",
            },
            {
                "key": "availability_percent",
                "value": payload.availability_percent,
                "unit": "%",
                "status": "assumed",
            },
        ]
    )
    inputs = SimulationInputs(
        daily_tasks=float(daily_tasks),
        operating_hours_per_day=float(shift_hours) * float(shifts_per_day),
        robot_speed_m_s=payload.robot_speed_m_s,
        handling_time_seconds=payload.handling_time_seconds,
        availability_percent=payload.availability_percent,
        robot_count=payload.robot_count,
    )
    try:
        result = calculate_simulation(inputs, route)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["warnings"] = route_warnings + result["warnings"]
    result["assumptions"] = assumptions
    result["plan_revision"] = revision
    run = SimulationRun(
        project_id=project_id,
        plan_revision=revision,
        model_version=SIMULATION_MODEL_VERSION,
        input_snapshot={**payload.model_dump(), "plan": plan_payload},
        result_snapshot=result,
    )
    session.add(run)
    session.flush()
    metrics = {
        "throughput_tasks_hour": (result["throughput_tasks_hour"], "заданий/ч"),
        "completed_tasks_day": (result["completed_tasks_day"], "заданий/сутки"),
        "cycle_time_seconds": (result["cycle_time_seconds"], "с"),
        "utilization_percent": (result["utilization_percent"], "%"),
    }
    for key, (value, unit) in metrics.items():
        session.add(
            SimulationMetric(
                simulation_run_id=run.id,
                key=key,
                value=value,
                unit=unit,
                status="assumed",
            )
        )
    session.commit()
    result["run_id"] = run.id
    return result
