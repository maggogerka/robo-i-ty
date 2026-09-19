"""Чистые формулы предварительной экономической оценки.

Все денежные значения передаются и возвращаются в рублях, периоды — в годах,
объёмы — в заданиях за сутки. Никаких обращений к БД модуль не выполняет.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import ceil


@dataclass(frozen=True)
class EconomicInputs:
    daily_tasks: float
    working_days_per_year: float
    shift_hours: float
    shifts_per_day: float
    target_staff: float
    monthly_labor_cost_rub: float
    payroll_factor: float
    robot_unit_price_rub: float
    horizon_years: int = 5
    peak_factor: float = 1.15
    robot_tasks_per_hour: float = 450
    robot_utilization: float = 0.78
    automation_share: float = 0.70
    infrastructure_share: float = 0.12
    software_share: float = 0.08
    integration_share: float = 0.10
    commissioning_share: float = 0.05
    training_share: float = 0.02
    reserve_share: float = 0.10
    annual_service_share: float = 0.08
    annual_license_per_robot_rub: float = 180_000
    annual_energy_per_robot_rub: float = 90_000
    annual_repairs_share: float = 0.03
    operating_staff: float = 3
    operating_staff_monthly_cost_rub: float = 120_000
    raas_monthly_per_robot_rub: float = 190_000
    raas_setup_share: float = 0.10


def required_robots(inputs: EconomicInputs) -> int:
    """Округлённый вверх парк для пикового суточного потока, шт."""

    productive_hours = inputs.shift_hours * inputs.shifts_per_day * inputs.robot_utilization
    capacity = inputs.robot_tasks_per_hour * productive_hours
    if capacity <= 0:
        raise ValueError("Производительность и рабочее время должны быть положительными")
    return max(1, ceil(inputs.daily_tasks * inputs.peak_factor / capacity))


def _payback(capex: float, annual_effect: float) -> float | None:
    """Простой срок окупаемости, лет; None при неположительном эффекте."""

    return round(capex / annual_effect, 2) if annual_effect > 0 else None


def calculate_economics(inputs: EconomicInputs) -> dict:
    """Сравнивает текущую работу, покупку и RaaS на заданном горизонте."""

    robots = required_robots(inputs)
    baseline_labor = (
        inputs.target_staff * inputs.monthly_labor_cost_rub * inputs.payroll_factor * 12
    )
    annual_tasks = inputs.daily_tasks * inputs.working_days_per_year
    retained_labor = baseline_labor * (1 - inputs.automation_share)
    equipment = robots * inputs.robot_unit_price_rub
    capex_lines = {
        "equipment": equipment,
        "infrastructure": equipment * inputs.infrastructure_share,
        "software": equipment * inputs.software_share,
        "integration": equipment * inputs.integration_share,
        "commissioning": equipment * inputs.commissioning_share,
        "training": equipment * inputs.training_share,
    }
    capex_lines["reserve"] = sum(capex_lines.values()) * inputs.reserve_share
    purchase_capex = sum(capex_lines.values())
    operating_staff_cost = (
        inputs.operating_staff
        * inputs.operating_staff_monthly_cost_rub
        * inputs.payroll_factor
        * 12
    )
    purchase_opex_lines = {
        "retained_labor": retained_labor,
        "service": equipment * inputs.annual_service_share,
        "licenses": robots * inputs.annual_license_per_robot_rub,
        "energy": robots * inputs.annual_energy_per_robot_rub,
        "repairs": equipment * inputs.annual_repairs_share,
        "operating_staff": operating_staff_cost,
    }
    purchase_opex = sum(purchase_opex_lines.values())
    purchase_effect = baseline_labor - purchase_opex
    purchase_tco = purchase_capex + purchase_opex * inputs.horizon_years
    purchase_roi = (
        ((baseline_labor * inputs.horizon_years - purchase_tco) / purchase_capex) * 100
        if purchase_capex > 0
        else None
    )

    raas_capex = equipment * inputs.raas_setup_share
    raas_payment = robots * inputs.raas_monthly_per_robot_rub * 12
    raas_opex_lines = {
        "retained_labor": retained_labor,
        "raas_payments": raas_payment,
        "energy": robots * inputs.annual_energy_per_robot_rub,
        "operating_staff": operating_staff_cost,
    }
    raas_opex = sum(raas_opex_lines.values())
    raas_effect = baseline_labor - raas_opex
    raas_tco = raas_capex + raas_opex * inputs.horizon_years
    raas_roi = (
        ((baseline_labor * inputs.horizon_years - raas_tco) / raas_capex) * 100
        if raas_capex > 0
        else None
    )

    def scenario(
        name: str,
        capex: float,
        opex: float,
        effect: float,
        tco: float,
        roi: float | None,
        lines: dict[str, float],
    ) -> dict:
        return {
            "name": name,
            "capex_rub": round(capex, 2),
            "annual_opex_rub": round(opex, 2),
            "annual_effect_rub": round(effect, 2),
            "payback_years": _payback(capex, effect),
            "roi_horizon_percent": round(roi, 2) if roi is not None else None,
            "tco_rub": round(tco, 2),
            "cost_per_task_rub": round(tco / (annual_tasks * inputs.horizon_years), 2)
            if annual_tasks > 0
            else None,
            "lines": {key: round(value, 2) for key, value in lines.items()},
        }

    baseline = scenario(
        "Текущая работа",
        0,
        baseline_labor,
        0,
        baseline_labor * inputs.horizon_years,
        None,
        {"labor": baseline_labor},
    )
    purchase = scenario(
        "Покупка и внедрение",
        purchase_capex,
        purchase_opex,
        purchase_effect,
        purchase_tco,
        purchase_roi,
        {**capex_lines, **purchase_opex_lines},
    )
    raas = scenario(
        "RaaS",
        raas_capex,
        raas_opex,
        raas_effect,
        raas_tco,
        raas_roi,
        {"setup": raas_capex, **raas_opex_lines},
    )
    return {
        "required_robots": robots,
        "horizon_years": inputs.horizon_years,
        "scenarios": {"baseline": baseline, "purchase": purchase, "raas": raas},
        "formula_note": (
            "ROI горизонта = (затраты базы за горизонт − TCO сценария) / CAPEX сценария × 100%."
        ),
        "assumptions": asdict(inputs),
    }


def calculate_sensitivity(inputs: EconomicInputs) -> list[dict]:
    """Считает эффект ±20% для цены, потока операций и стоимости труда."""

    variants = {
        "Цена оборудования": "robot_unit_price_rub",
        "Объём операций": "daily_tasks",
        "Стоимость труда": "monthly_labor_cost_rub",
    }
    output: list[dict] = []
    for label, field in variants.items():
        base = getattr(inputs, field)
        points = []
        for multiplier in (0.8, 1.0, 1.2):
            changed = replace(inputs, **{field: base * multiplier})
            result = calculate_economics(changed)["scenarios"]["purchase"]
            points.append(
                {
                    "change_percent": round((multiplier - 1) * 100),
                    "annual_effect_rub": result["annual_effect_rub"],
                    "payback_years": result["payback_years"],
                }
            )
        output.append({"factor": label, "points": points})
    return output
