"""Детерминированный и объяснимый подбор роботизированных решений."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import RobotSolution

WEIGHTS = {
    "technical": 0.30,
    "performance": 0.20,
    "economics": 0.25,
    "infrastructure": 0.10,
    "maturity": 0.10,
    "data_quality": 0.05,
}


@dataclass(frozen=True)
class Constraint:
    code: str
    label: str
    status: str
    detail: str


def _warehouse_compatible(solution: RobotSolution) -> bool:
    haystack = " ".join(
        filter(
            None,
            [solution.process, solution.description, solution.catalog_type, solution.subtype],
        )
    ).lower()
    return any(token in haystack for token in ("склад", "внутрисклад", "паллет", "сортиров"))


def _constraints(
    solution: RobotSolution, object_type_code: str, parameters: dict[str, Any]
) -> list[Constraint]:
    checks: list[Constraint] = []
    if object_type_code == "warehouse":
        compatible = _warehouse_compatible(solution)
        checks.append(
            Constraint(
                "object_compatibility",
                "Совместимость со складским процессом",
                "passed" if compatible else "failed",
                "В карточке есть складской сценарий"
                if compatible
                else "Складская применимость не подтверждена источником",
            )
        )
    else:
        industry_tokens = {
            "airport": ("транспорт", "логист", "уборк"),
            "healthcare": ("мед", "уборк", "логист"),
        }[object_type_code]
        haystack = " ".join(
            filter(None, [solution.industry, solution.process, solution.description])
        ).lower()
        compatible = any(token in haystack for token in industry_tokens)
        checks.append(
            Constraint(
                "object_compatibility",
                "Совместимость с типом объекта",
                "passed" if compatible else "failed",
                "Категория применима" if compatible else "Применимость не подтверждена",
            )
        )

    required_payload = parameters.get("payload_kg")
    if not isinstance(required_payload, int | float):
        checks.append(Constraint("payload", "Грузоподъёмность", "unknown", "Нет требования"))
    elif solution.max_payload_kg is None:
        checks.append(
            Constraint(
                "payload",
                "Грузоподъёмность",
                "unknown",
                "ТТХ отсутствует в ценовом источнике — нужна проверка производителя",
            )
        )
    elif solution.max_payload_kg >= required_payload:
        checks.append(
            Constraint(
                "payload",
                "Грузоподъёмность",
                "passed",
                f"{solution.max_payload_kg:g} кг ≥ требуемых {required_payload:g} кг",
            )
        )
    else:
        checks.append(
            Constraint(
                "payload",
                "Грузоподъёмность",
                "failed",
                f"{solution.max_payload_kg:g} кг < требуемых {required_payload:g} кг",
            )
        )

    budget = parameters.get("budget_mln_rub")
    if solution.price_rub is None or not isinstance(budget, int | float):
        checks.append(
            Constraint("budget", "Бюджет оборудования", "unknown", "Нет сопоставимых данных")
        )
    elif solution.price_rub <= budget * 1_000_000:
        checks.append(
            Constraint("budget", "Бюджет оборудования", "passed", "Цена единицы ниже бюджета")
        )
    else:
        checks.append(
            Constraint(
                "budget",
                "Бюджет оборудования",
                "failed",
                "Цена одной единицы превышает весь заявленный CAPEX-бюджет",
            )
        )
    return checks


def score_solution(
    solution: RobotSolution,
    object_type_code: str,
    parameters: dict[str, Any],
    has_case: bool,
) -> dict[str, Any]:
    constraints = _constraints(solution, object_type_code, parameters)
    eligible = not any(item.status == "failed" for item in constraints)
    unknown_count = sum(item.status == "unknown" for item in constraints)

    technical = 100.0 if solution.max_payload_kg is not None else 60.0
    status_score = {"operation": 95.0, "piloting": 68.0, "rnd": 38.0}.get(solution.status, 45.0)
    market_score = (solution.market_potential or 2.5) / 5 * 100
    performance = status_score
    budget = float(parameters.get("budget_mln_rub") or 0) * 1_000_000
    if solution.price_rub and budget:
        economics = max(35.0, min(100.0, 110 - (solution.price_rub / budget) * 100))
    else:
        economics = 45.0
    infrastructure = (
        82.0
        if solution.catalog_type
        in {
            "Мобильные роботы",
            "Автономные наземные транспортные средства",
        }
        else 62.0
    )
    maturity = min(100.0, ((solution.trl or 4) / 9 * 75) + (25 if has_case else 0))
    data_quality = solution.data_completeness * 100

    raw = {
        "technical": technical,
        "performance": performance,
        "economics": economics,
        "infrastructure": infrastructure,
        "maturity": (maturity + market_score) / 2,
        "data_quality": data_quality,
    }
    contributions = {key: round(value * WEIGHTS[key], 2) for key, value in raw.items()}
    score = round(sum(contributions.values()), 2) if eligible else 0.0
    reasons = [item.detail for item in constraints if item.status == "passed"]
    missing = [item.detail for item in constraints if item.status == "unknown"]
    return {
        "solution_id": solution.id,
        "name": solution.name,
        "manufacturer": solution.manufacturer,
        "price_rub": solution.price_rub,
        "status": solution.status,
        "eligible": eligible,
        "score": score,
        "criteria": {key: round(value, 2) for key, value in raw.items()},
        "contributions": contributions,
        "constraints": [asdict(item) for item in constraints],
        "reasons": reasons,
        "missing_data": missing,
        "assumptions": [
            "Инфраструктурная готовность оценена по классу решения",
            "Производительность оценена по стадии готовности, так как ТТХ отсутствуют",
        ],
        "requires_verification": unknown_count > 0,
    }


def rank_solutions(
    solutions: list[RobotSolution],
    object_type_code: str,
    parameters: dict[str, Any],
    solution_ids_with_cases: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored = [
        score_solution(item, object_type_code, parameters, item.id in solution_ids_with_cases)
        for item in solutions
    ]
    eligible = sorted(
        (item for item in scored if item["eligible"]),
        key=lambda item: (-item["score"], item["name"], item["solution_id"]),
    )
    excluded = sorted(
        (item for item in scored if not item["eligible"]),
        key=lambda item: (item["name"], item["solution_id"]),
    )
    for index, item in enumerate(eligible, start=1):
        item["rank"] = index
    return eligible, excluded
