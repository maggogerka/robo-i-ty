from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..economics import EconomicInputs, calculate_economics, calculate_sensitivity
from ..matching import WEIGHTS, rank_solutions
from ..models import (
    DeploymentCase,
    MatchingCandidate,
    MatchingRun,
    Project,
    ProjectParameterValue,
    RobotSolution,
    User,
)
from ..schemas import EconomicsRequest
from ..security import get_current_user

router = APIRouter(prefix="/projects", tags=["Аналитика"])


def _project(project_id: str, user: User, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None or (project.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


def _parameters(project_id: str, session: Session) -> dict:
    return {
        item.definition_code: item.value
        for item in session.exec(
            select(ProjectParameterValue).where(ProjectParameterValue.project_id == project_id)
        )
    }


def _matching(project: Project, parameters: dict, session: Session):
    solutions = list(session.exec(select(RobotSolution)))
    case_ids = {item.solution_id for item in session.exec(select(DeploymentCase))}
    return rank_solutions(solutions, project.object_type_code, parameters, case_ids)


@router.post("/{project_id}/matching")
def run_matching(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = _project(project_id, user, session)
    parameters = _parameters(project.id, session)
    eligible, excluded = _matching(project, parameters, session)
    run = MatchingRun(project_id=project.id, input_snapshot=parameters)
    session.add(run)
    session.flush()
    for item in eligible[:20]:
        session.add(
            MatchingCandidate(
                matching_run_id=run.id,
                solution_id=item["solution_id"],
                rank=item["rank"],
                score=item["score"],
                eligible=True,
                explanation=item,
            )
        )
    session.commit()
    return {
        "run_id": run.id,
        "model_version": run.model_version,
        "weights": WEIGHTS,
        "candidates": eligible[:20],
        "excluded": excluded[:20],
        "disclaimer": (
            "Подбор предварительный. Неизвестные ТТХ не считаются пройденными "
            "ограничениями и требуют подтверждения производителя."
        ),
    }


@router.post("/{project_id}/economics")
def run_economics(
    project_id: str,
    payload: EconomicsRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = _project(project_id, user, session)
    values = _parameters(project.id, session)
    solution = session.get(RobotSolution, payload.solution_id) if payload.solution_id else None
    if solution is None:
        eligible, _ = _matching(project, values, session)
        if not eligible:
            raise HTTPException(status_code=422, detail="Нет применимых решений для расчёта")
        solution = session.get(RobotSolution, eligible[0]["solution_id"])
    if solution is None or solution.price_rub is None:
        raise HTTPException(status_code=422, detail="У выбранного решения нет цены")

    defaults = {
        "daily_tasks": float(values.get("daily_tasks") or 1_000),
        "working_days_per_year": float(values.get("working_days_per_year") or 365),
        "shift_hours": float(values.get("shift_hours") or 8),
        "shifts_per_day": float(values.get("shifts_per_day") or 2),
        "target_staff": float(values.get("target_staff") or 20),
        "monthly_labor_cost_rub": float(values.get("monthly_labor_cost_rub") or 80_000),
        "payroll_factor": float(values.get("payroll_factor") or 1.302),
        "robot_unit_price_rub": float(solution.price_rub),
        "horizon_years": int(values.get("horizon_years") or 5),
        "peak_factor": float(values.get("peak_factor") or 1.15),
    }
    allowed = set(EconomicInputs.__dataclass_fields__)
    unknown = set(payload.overrides) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail=f"Неизвестные допущения: {sorted(unknown)}")
    defaults.update(payload.overrides)
    try:
        inputs = EconomicInputs(**defaults)
        result = calculate_economics(inputs)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result.update(
        {
            "solution": {
                "id": solution.id,
                "name": solution.name,
                "manufacturer": solution.manufacturer,
                "price_rub": solution.price_rub,
            },
            "sensitivity": calculate_sensitivity(inputs),
            "assumption_status": "assumed",
            "disclaimer": (
                "Предварительная оценка на демонстрационных допущениях; требуется "
                "инженерное обследование и коммерческое предложение."
            ),
        }
    )
    return result
