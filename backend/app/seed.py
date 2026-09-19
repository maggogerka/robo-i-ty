from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from .config import get_settings
from .models import (
    DeploymentCase,
    ObjectParameterDefinition,
    ObjectType,
    RobotSolution,
    SourceEvidence,
    User,
)
from .security import hash_password


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def seed_database(session: Session) -> None:
    settings = get_settings()
    accounts = (
        (settings.demo_user_email, settings.demo_user_password, "user"),
        (settings.demo_admin_email, settings.demo_admin_password, "admin"),
    )
    for email, password, role in accounts:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            session.add(User(email=email, password_hash=hash_password(password), role=role))

    object_path = settings.seed_dir / "object_types.json"
    catalog_path = settings.seed_dir / "catalog.json"
    if not object_path.exists() or not catalog_path.exists():
        raise RuntimeError(
            "Seed не найден. Выполните `python scripts/build_seed.py` из корня проекта."
        )

    for source in (
        SourceEvidence(
            id="source-object-dataset",
            title="Демонстрационные параметры трёх типов объектов",
            source_type="xlsx",
            source_name="Датасеты_хакатон.xlsx",
            source_date="2026-09-20",
        ),
        SourceEvidence(
            id="source-price-catalog",
            title="Каталог решений с ценами и кейсами",
            source_type="csv",
            source_name="catalog_export_v4.csv",
            source_date="2026-09-20",
        ),
    ):
        if session.get(SourceEvidence, source.id) is None:
            session.add(source)

    for item in _read_json(object_path):
        object_type = session.get(ObjectType, item["code"])
        if object_type is None:
            object_type = ObjectType(
                code=item["code"], name=item["name"], readiness=item["readiness"]
            )
            session.add(object_type)
        else:
            object_type.name = item["name"]
            object_type.readiness = item["readiness"]
        for parameter in item["parameters"]:
            definition = session.exec(
                select(ObjectParameterDefinition).where(
                    ObjectParameterDefinition.object_type_code == item["code"],
                    ObjectParameterDefinition.code == parameter["code"],
                )
            ).first()
            values = {"object_type_code": item["code"], **parameter}
            if definition is None:
                session.add(ObjectParameterDefinition(**values))
            else:
                for key, value in parameter.items():
                    setattr(definition, key, value)

    catalog = _read_json(catalog_path)
    for item in catalog["products"]:
        solution = session.get(RobotSolution, item["id"])
        if solution is None:
            session.add(RobotSolution(**item))
        else:
            for key, value in item.items():
                if key != "id":
                    setattr(solution, key, value)
    for item in catalog["cases"]:
        if session.get(DeploymentCase, item["id"]) is None:
            session.add(DeploymentCase(**item))
    session.commit()
