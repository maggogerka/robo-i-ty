from app.economics import (
    EconomicInputs,
    calculate_economics,
    calculate_sensitivity,
    required_robots,
)


def inputs(**overrides):
    values = {
        "daily_tasks": 100_000,
        "working_days_per_year": 365,
        "shift_hours": 11,
        "shifts_per_day": 2,
        "target_staff": 100,
        "monthly_labor_cost_rub": 100_000,
        "payroll_factor": 1.302,
        "robot_unit_price_rub": 2_700_000,
    }
    values.update(overrides)
    return EconomicInputs(**values)


def test_robot_count_is_rounded_up_and_deterministic():
    assert required_robots(inputs()) == 15
    assert required_robots(inputs()) == required_robots(inputs())


def test_three_scenarios_and_transparent_formula():
    result = calculate_economics(inputs())
    assert set(result["scenarios"]) == {"baseline", "purchase", "raas"}
    assert result["scenarios"]["baseline"]["capex_rub"] == 0
    assert result["scenarios"]["purchase"]["tco_rub"] > 0
    assert "ROI" in result["formula_note"]
    assert result["model_version"] == "2026.09.2"


def test_non_positive_effect_has_no_fake_payback():
    result = calculate_economics(inputs(robot_unit_price_rub=1_000_000_000))
    assert result["scenarios"]["purchase"]["annual_effect_rub"] < 0
    assert result["scenarios"]["purchase"]["payback_years"] is None


def test_sensitivity_contains_three_factors_and_three_points():
    result = calculate_sensitivity(inputs())
    assert [item["factor"] for item in result] == [
        "Цена оборудования",
        "Объём операций",
        "Стоимость труда",
    ]
    assert all(len(item["points"]) == 3 for item in result)
