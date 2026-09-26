from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    AuditEvent,
    ObjectParameterDefinition,
    Project,
    ProjectParameterValue,
    SimulationRun,
    User,
)
from ..schemas import EconomicsRequest
from ..security import InMemoryRateLimiter, get_current_user
from .analysis import _matching, _parameters, run_economics

router = APIRouter(prefix="/projects", tags=["Отчёты и экспорт"])
export_limiter = InMemoryRateLimiter(limit=15, window_seconds=60)

template_environment = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
    autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
)


def _format_number(value: Any) -> str:
    if value is None:
        return "не рассчитывается"
    if isinstance(value, int | float):
        digits = 0 if float(value).is_integer() else 1
        return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")
    return str(value)


def _format_value(value: Any) -> str:
    if value is None:
        return "не задано"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, int | float):
        return _format_number(value)
    return str(value)


template_environment.filters["num"] = _format_number
template_environment.filters["value"] = _format_value


def _project_for_user(project_id: str, user: User, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None or (project.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


def _snapshot(project: Project, user: User, session: Session) -> dict[str, Any]:
    values = list(
        session.exec(
            select(ProjectParameterValue).where(ProjectParameterValue.project_id == project.id)
        )
    )
    definitions = {
        item.code: item
        for item in session.exec(
            select(ObjectParameterDefinition).where(
                ObjectParameterDefinition.object_type_code == project.object_type_code
            )
        )
    }
    parameters = []
    for stored in values:
        definition = definitions.get(stored.definition_code)
        parameters.append(
            {
                "code": stored.definition_code,
                "name": definition.name if definition else stored.definition_code,
                "value": stored.value,
                "unit": definition.unit if definition else None,
                "source_status": stored.source_status,
                "source_name": definition.source_name if definition else None,
            }
        )
    parameters.sort(key=lambda item: item["name"])

    raw_values = _parameters(project.id, session)
    candidates, excluded = _matching(project, raw_values, session)
    economics = None
    if candidates:
        try:
            economics = run_economics(
                project.id,
                EconomicsRequest(solution_id=candidates[0]["solution_id"]),
                user,
                session,
            )
        except HTTPException:
            economics = None
    latest_simulation = session.exec(
        select(SimulationRun)
        .where(SimulationRun.project_id == project.id)
        .order_by(SimulationRun.created_at.desc())
    ).first()
    return {
        "project": project.model_dump(),
        "parameters": parameters,
        "candidates": candidates[:10],
        "excluded_count": len(excluded),
        "economics": economics,
        "simulation": latest_simulation.result_snapshot if latest_simulation else None,
        "generated_at": datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
    }


def _safe_cell(value: Any) -> Any:
    """Не даёт табличным редакторам интерпретировать текст как формулу."""

    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def _csv_bytes(snapshot: dict[str, Any]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Раздел", "Код/название", "Значение", "Единица", "Статус", "Источник"])
    project = snapshot["project"]
    writer.writerow(
        [
            "Проект",
            "Название",
            _safe_cell(project["name"]),
            "",
            "source_present",
            "База проекта",
        ]
    )
    for item in snapshot["parameters"]:
        writer.writerow(
            [
                "Входной параметр",
                _safe_cell(item["name"]),
                _safe_cell(_format_value(item["value"])),
                _safe_cell(item["unit"]),
                item["source_status"],
                _safe_cell(item["source_name"] or "Пользователь"),
            ]
        )
    for item in snapshot["candidates"]:
        writer.writerow(
            [
                "Подбор",
                _safe_cell(f"#{item['rank']} {item['name']}"),
                item["score"],
                "балл 0–100",
                "assumed" if item["requires_verification"] else "source_present",
                "Модель подбора 2026.09.1",
            ]
        )
    economics = snapshot["economics"]
    if economics:
        for scenario_key, scenario in economics["scenarios"].items():
            for metric, unit in (
                ("capex_rub", "₽"),
                ("annual_opex_rub", "₽/год"),
                ("annual_effect_rub", "₽/год"),
                ("payback_years", "лет"),
                ("tco_rub", "₽"),
            ):
                writer.writerow(
                    [
                        f"Экономика: {scenario_key}",
                        metric,
                        _safe_cell(_format_value(scenario[metric])),
                        unit,
                        "assumed",
                        f"Экономическая модель {economics['model_version']}",
                    ]
                )
    simulation = snapshot["simulation"]
    if simulation:
        for metric, unit in (
            ("route_distance_m", "м"),
            ("cycle_time_seconds", "с"),
            ("throughput_tasks_hour", "заданий/ч"),
            ("completed_tasks_day", "заданий/сутки"),
            ("utilization_percent", "%"),
        ):
            writer.writerow(
                [
                    "2D-симуляция",
                    metric,
                    simulation[metric],
                    unit,
                    "assumed",
                    f"Модель симуляции {simulation['model_version']}",
                ]
            )
    return ("\ufeffsep=;\r\n" + stream.getvalue()).encode("utf-8")


def _audit_export(project: Project, user: User, export_type: str, session: Session) -> None:
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="project.export",
            entity_type="Project",
            entity_id=project.id,
            details={"format": export_type},
        )
    )
    session.commit()


def _download_headers(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }


@router.get("/{project_id}/exports/analysis.csv")
def export_csv(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    export_limiter.check(request)
    project = _project_for_user(project_id, user, session)
    snapshot = _snapshot(project, user, session)
    content = _csv_bytes(snapshot)
    _audit_export(project, user, "csv", session)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers=_download_headers(f"robo-analysis-{project.id[:8]}.csv"),
    )


@router.get("/{project_id}/reports/summary.pdf")
def export_pdf(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    export_limiter.check(request)
    project = _project_for_user(project_id, user, session)
    snapshot = _snapshot(project, user, session)
    html = template_environment.get_template("report.html").render(**snapshot)
    try:
        from weasyprint import HTML

        pdf = HTML(
            string=html,
            url_fetcher=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ValueError("Внешние ресурсы в отчёте запрещены")
            ),
        ).write_pdf()
    except (ImportError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF-движок недоступен; используйте CSV или Docker-окружение",
        ) from exc
    _audit_export(project, user, "pdf", session)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers=_download_headers(f"robo-report-{project.id[:8]}.pdf"),
    )
