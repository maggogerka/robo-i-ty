from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    AuditEvent,
    ObjectParameterDefinition,
    ObjectType,
    Project,
    ProjectParameterValue,
    User,
)
from ..schemas import ParameterUpdate, ProjectCreate, ProjectSummary
from ..security import get_current_user

router = APIRouter(tags=["Проекты и объекты"])


def _project_for_user(project_id: str, user: User, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


def _project_payload(project: Project, session: Session) -> dict[str, Any]:
    definitions = list(
        session.exec(
            select(ObjectParameterDefinition)
            .where(ObjectParameterDefinition.object_type_code == project.object_type_code)
            .order_by(ObjectParameterDefinition.section, ObjectParameterDefinition.name)
        )
    )
    values = {
        item.definition_code: item
        for item in session.exec(
            select(ProjectParameterValue).where(ProjectParameterValue.project_id == project.id)
        )
    }
    parameters = []
    for definition in definitions:
        stored = values.get(definition.code)
        parameters.append(
            {
                "code": definition.code,
                "name": definition.name,
                "section": definition.section,
                "unit": definition.unit,
                "value": stored.value if stored else definition.baseline,
                "original_value": stored.original_value if stored else definition.baseline,
                "minimum": definition.minimum,
                "maximum": definition.maximum,
                "required": definition.required,
                "value_type": definition.value_type,
                "note": definition.note,
                "source_status": stored.source_status if stored else definition.source_status,
                "source_name": definition.source_name,
                "changed_at": stored.changed_at if stored else None,
            }
        )
    return {
        "id": project.id,
        "name": project.name,
        "object_type_code": project.object_type_code,
        "calculation_version": project.calculation_version,
        "is_demo": project.is_demo,
        "parameters": parameters,
    }


def _fill_defaults(project: Project, session: Session) -> None:
    definitions = session.exec(
        select(ObjectParameterDefinition).where(
            ObjectParameterDefinition.object_type_code == project.object_type_code
        )
    )
    for definition in definitions:
        session.add(
            ProjectParameterValue(
                project_id=project.id,
                definition_code=definition.code,
                value=definition.baseline,
                original_value=definition.baseline,
                source_status=definition.source_status,
                source_comment=f"Базовое значение из {definition.source_name}",
            )
        )


@router.get("/object-types")
def object_types(session: Session = Depends(get_session)):
    result = []
    for item in session.exec(select(ObjectType).order_by(ObjectType.name)):
        count = len(
            list(
                session.exec(
                    select(ObjectParameterDefinition).where(
                        ObjectParameterDefinition.object_type_code == item.code
                    )
                )
            )
        )
        result.append({**item.model_dump(), "parameter_count": count})
    return result


@router.get("/object-types/{object_type_code}")
def object_type(object_type_code: str, session: Session = Depends(get_session)):
    item = session.get(ObjectType, object_type_code)
    if item is None:
        raise HTTPException(status_code=404, detail="Тип объекта не найден")
    definitions = list(
        session.exec(
            select(ObjectParameterDefinition)
            .where(ObjectParameterDefinition.object_type_code == object_type_code)
            .order_by(ObjectParameterDefinition.section, ObjectParameterDefinition.name)
        )
    )
    return {**item.model_dump(), "parameters": definitions}


@router.get("/projects", response_model=list[ProjectSummary])
def projects(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Project)
    if user.role != "admin":
        query = query.where(Project.owner_id == user.id)
    return list(session.exec(query.order_by(Project.updated_at.desc())))


@router.post("/projects", response_model=ProjectSummary)
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if session.get(ObjectType, payload.object_type_code) is None:
        raise HTTPException(status_code=422, detail="Неизвестный тип объекта")
    project = Project(
        owner_id=user.id, name=payload.name, object_type_code=payload.object_type_code
    )
    session.add(project)
    session.flush()
    _fill_defaults(project, session)
    session.commit()
    session.refresh(project)
    return project


@router.post("/projects/demo")
def demo_project(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    existing = session.exec(
        select(Project).where(Project.owner_id == user.id, Project.is_demo.is_(True))
    ).first()
    if existing:
        return _project_payload(existing, session)
    project = Project(
        owner_id=user.id,
        name="Демо: распределительный склад",
        object_type_code="warehouse",
        is_demo=True,
    )
    session.add(project)
    session.flush()
    _fill_defaults(project, session)
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="project.demo.create",
            entity_type="Project",
            entity_id=project.id,
        )
    )
    session.commit()
    session.refresh(project)
    return _project_payload(project, session)


@router.get("/projects/{project_id}")
def project_details(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _project_payload(_project_for_user(project_id, user, session), session)


@router.patch("/projects/{project_id}/parameters")
def update_parameters(
    project_id: str,
    payload: ParameterUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = _project_for_user(project_id, user, session)
    definitions = {
        item.code: item
        for item in session.exec(
            select(ObjectParameterDefinition).where(
                ObjectParameterDefinition.object_type_code == project.object_type_code
            )
        )
    }
    errors = []
    for code, value in payload.values.items():
        definition = definitions.get(code)
        if definition is None:
            errors.append({"code": code, "message": "Неизвестный параметр"})
            continue
        if definition.value_type == "number" and not isinstance(value, int | float):
            errors.append({"code": code, "message": "Ожидается число"})
            continue
        if isinstance(value, int | float):
            if definition.minimum is not None and value < definition.minimum:
                errors.append(
                    {"code": code, "message": f"Минимальное значение: {definition.minimum:g}"}
                )
            if definition.maximum is not None and value > definition.maximum:
                errors.append(
                    {"code": code, "message": f"Максимальное значение: {definition.maximum:g}"}
                )
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    for code, value in payload.values.items():
        stored = session.exec(
            select(ProjectParameterValue).where(
                ProjectParameterValue.project_id == project.id,
                ProjectParameterValue.definition_code == code,
            )
        ).first()
        if stored is None:
            stored = ProjectParameterValue(
                project_id=project.id,
                definition_code=code,
                value=value,
                original_value=definitions[code].baseline,
            )
            session.add(stored)
        else:
            stored.value = value
        stored.source_status = "assumed"
        stored.source_comment = "Изменено пользователем"
        stored.changed_by = user.id
        stored.changed_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="project.parameters.update",
            entity_type="Project",
            entity_id=project.id,
            details={"fields": sorted(payload.values)},
        )
    )
    session.commit()
    return _project_payload(project, session)
