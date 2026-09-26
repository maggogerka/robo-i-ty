"""Детерминированный и объяснимый подбор роботизированных решений."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import RobotSolution
from .simulation import Point, Rect, build_astar_route

MATCHING_MODEL_VERSION = "2026.09.2"
WEIGHTS = {
    "functional": 0.25,
    "plan_feasibility": 0.25,
    "performance": 0.20,
    "economics": 0.15,
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


def _object_constraint(solution: RobotSolution, object_type_code: str) -> Constraint:
    if object_type_code == "warehouse":
        compatible = _warehouse_compatible(solution)
        return Constraint(
            "object_compatibility",
            "Совместимость со складским процессом",
            "passed" if compatible else "failed",
            "В карточке есть складской сценарий"
            if compatible
            else "Складская применимость не подтверждена источником",
        )
    industry_tokens = {
        "airport": ("транспорт", "логист", "уборк"),
        "healthcare": ("мед", "уборк", "логист"),
    }[object_type_code]
    haystack = " ".join(
        filter(None, [solution.industry, solution.process, solution.description])
    ).lower()
    compatible = any(token in haystack for token in industry_tokens)
    return Constraint(
        "object_compatibility",
        "Совместимость с типом объекта",
        "passed" if compatible else "failed",
        "Категория применима" if compatible else "Применимость не подтверждена",
    )


def _payload_constraint(solution: RobotSolution, parameters: dict[str, Any]) -> Constraint:
    required_payload = parameters.get("payload_kg")
    if not isinstance(required_payload, int | float):
        return Constraint("payload", "Грузоподъёмность", "unknown", "Нет требования по массе, кг")
    if solution.max_payload_kg is None:
        return Constraint(
            "payload",
            "Грузоподъёмность",
            "unknown",
            "Грузоподъёмность, кг, отсутствует в источнике — нужна проверка производителя",
        )
    if solution.max_payload_kg >= required_payload:
        return Constraint(
            "payload",
            "Грузоподъёмность",
            "passed",
            f"{solution.max_payload_kg:g} кг ≥ требуемых {required_payload:g} кг",
        )
    return Constraint(
        "payload",
        "Грузоподъёмность",
        "failed",
        f"{solution.max_payload_kg:g} кг < требуемых {required_payload:g} кг",
    )


def _budget_constraint(solution: RobotSolution, parameters: dict[str, Any]) -> Constraint:
    budget = parameters.get("budget_mln_rub")
    if solution.price_rub is None or not isinstance(budget, int | float):
        return Constraint(
            "budget", "Бюджет оборудования", "unknown", "Нет сопоставимых ценовых данных, руб."
        )
    if solution.price_rub <= budget * 1_000_000:
        return Constraint(
            "budget", "Бюджет оборудования", "passed", "Цена единицы ниже CAPEX-бюджета"
        )
    return Constraint(
        "budget",
        "Бюджет оборудования",
        "failed",
        "Цена одной единицы превышает весь заявленный CAPEX-бюджет",
    )


def _aisle_constraint(solution: RobotSolution, parameters: dict[str, Any]) -> Constraint:
    available = parameters.get("working_aisle_width_m")
    if not isinstance(available, int | float):
        available = parameters.get("main_aisle_width_m")
    if solution.width_m is None:
        return Constraint(
            "aisle_width",
            "Ширина прохода",
            "unknown",
            "Ширина робота, м, отсутствует в источнике — ограничение не считается пройденным",
        )
    if not isinstance(available, int | float):
        return Constraint(
            "aisle_width",
            "Ширина прохода",
            "unknown",
            "Ширина прохода, м, не задана в параметрах объекта",
        )
    required = solution.width_m + 0.3
    if required <= available:
        return Constraint(
            "aisle_width",
            "Ширина прохода",
            "passed",
            (
                f"Требуется {required:g} м при доступных {available:g} м; "
                "запас 0,15 м с каждой стороны"
            ),
        )
    return Constraint(
        "aisle_width",
        "Ширина прохода",
        "failed",
        f"Требуется {required:g} м при доступных {available:g} м",
    )


def _route_constraint(solution: RobotSolution, plan: dict[str, Any] | None) -> Constraint:
    if solution.width_m is None:
        return Constraint(
            "route_feasibility",
            "Проходимость по плану",
            "unknown",
            "Без ширины робота нельзя проверить маршрут на плане",
        )
    if not plan or plan.get("review_status") != "confirmed":
        return Constraint(
            "route_feasibility",
            "Проходимость по плану",
            "unknown",
            "Подтверждённый 2D-план отсутствует",
        )
    if plan.get("asset_id") and plan.get("scale_status") != "confirmed":
        return Constraint(
            "route_feasibility",
            "Проходимость по плану",
            "unknown",
            "Масштаб загруженного плана не подтверждён",
        )
    elements = plan.get("elements") or []
    pickup = next((item for item in elements if item.get("kind") == "pickup"), None)
    dropoff = next((item for item in elements if item.get("kind") == "dropoff"), None)
    if not pickup or not dropoff:
        return Constraint(
            "route_feasibility",
            "Проходимость по плану",
            "unknown",
            "На плане нет контрольных точек забора и доставки",
        )

    def center(item: dict[str, Any]) -> Point:
        return Point(item["x_m"] + item["width_m"] / 2, item["y_m"] + item["height_m"] / 2)

    obstacles = [
        Rect(item["x_m"], item["y_m"], item["width_m"], item["height_m"])
        for item in elements
        if item.get("kind") in {"wall", "storage", "obstacle", "restricted_zone"}
    ]
    route, warnings = build_astar_route(
        center(pickup),
        center(dropoff),
        obstacles,
        width_m=plan["width_m"],
        height_m=plan["height_m"],
        clearance_m=solution.width_m / 2 + 0.15,
    )
    if route:
        return Constraint(
            "route_feasibility",
            "Проходимость по плану",
            "passed",
            "A* нашёл маршрут с учётом половины ширины робота и запаса 0,15 м",
        )
    return Constraint(
        "route_feasibility",
        "Проходимость по плану",
        "failed",
        warnings[-1] if warnings else "Безопасный маршрут не найден",
    )


def _constraints(
    solution: RobotSolution,
    object_type_code: str,
    parameters: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[Constraint]:
    return [
        _object_constraint(solution, object_type_code),
        _payload_constraint(solution, parameters),
        _budget_constraint(solution, parameters),
        _aisle_constraint(solution, parameters),
        _route_constraint(solution, plan),
    ]


def _criterion_score(constraints: list[Constraint], codes: set[str]) -> float:
    values = [
        {"passed": 100.0, "unknown": 45.0, "failed": 0.0}[item.status]
        for item in constraints
        if item.code in codes
    ]
    return sum(values) / len(values) if values else 45.0


def score_solution(
    solution: RobotSolution,
    object_type_code: str,
    parameters: dict[str, Any],
    has_case: bool,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    constraints = _constraints(solution, object_type_code, parameters, plan)
    eligible = not any(item.status == "failed" for item in constraints)
    unknown_count = sum(item.status == "unknown" for item in constraints)

    functional = _criterion_score(constraints, {"object_compatibility", "payload"})
    plan_feasibility = _criterion_score(constraints, {"aisle_width", "route_feasibility"})
    performance = {"operation": 95.0, "piloting": 68.0, "rnd": 38.0}.get(solution.status, 45.0)
    budget = parameters.get("budget_mln_rub")
    if solution.price_rub is not None and isinstance(budget, int | float) and budget > 0:
        economics = max(35.0, min(100.0, 110 - solution.price_rub / (budget * 1_000_000) * 100))
    else:
        economics = 45.0
    trl_score = solution.trl / 9 * 75 if solution.trl is not None else 45.0
    market_score = (
        solution.market_potential / 5 * 100 if solution.market_potential is not None else 50.0
    )
    maturity = min(100.0, (trl_score + market_score) / 2 + (12.5 if has_case else 0))
    data_quality = solution.data_completeness * 100

    raw = {
        "functional": functional,
        "plan_feasibility": plan_feasibility,
        "performance": performance,
        "economics": economics,
        "maturity": maturity,
        "data_quality": data_quality,
    }
    contributions = {key: round(value * WEIGHTS[key], 2) for key, value in raw.items()}
    score = round(sum(contributions.values()), 2) if eligible else 0.0
    assumptions = [
        "Производительность оценена по стадии готовности: количественные ТТХ отсутствуют",
    ]
    if solution.width_m is not None:
        assumptions.append("Контур робота аппроксимирован окружностью по его ширине, м")
    if solution.trl is None or solution.market_potential is None:
        assumptions.append("Отсутствующая оценка зрелости заменена нейтральной оценкой, не нулём")
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
        "reasons": [item.detail for item in constraints if item.status == "passed"],
        "missing_data": [item.detail for item in constraints if item.status == "unknown"],
        "assumptions": assumptions,
        "requires_verification": unknown_count > 0,
    }


def rank_solutions(
    solutions: list[RobotSolution],
    object_type_code: str,
    parameters: dict[str, Any],
    solution_ids_with_cases: set[str],
    plan: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored = [
        score_solution(
            item,
            object_type_code,
            parameters,
            item.id in solution_ids_with_cases,
            plan,
        )
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
