from app.matching import MATCHING_MODEL_VERSION, WEIGHTS, rank_solutions, score_solution
from app.models import RobotSolution


def solution(
    id_: str,
    name: str,
    payload: float | None,
    price: float = 2_000_000,
    width_m: float | None = None,
):
    return RobotSolution(
        id=id_,
        name=name,
        manufacturer="Тестовый производитель",
        catalog_type="Мобильные роботы",
        status="operation",
        description="AMR для склада и перемещения паллет",
        process="Внутрискладская логистика",
        trl=8,
        market_potential=4,
        industry="Торговля и услуги",
        price_rub=price,
        max_payload_kg=payload,
        width_m=width_m,
        data_completeness=0.9,
        source_name="test",
    )


def test_known_failed_payload_excludes_solution():
    item = score_solution(
        solution("small", "Малый", 100),
        "warehouse",
        {"payload_kg": 800, "budget_mln_rub": 80},
        True,
    )
    assert item["eligible"] is False
    assert any(c["code"] == "payload" and c["status"] == "failed" for c in item["constraints"])


def test_unknown_payload_is_visible_but_requires_verification():
    item = score_solution(
        solution("unknown", "Без ТТХ", None),
        "warehouse",
        {"payload_kg": 800, "budget_mln_rub": 80},
        True,
    )
    assert item["eligible"] is True
    assert item["requires_verification"] is True
    assert item["missing_data"]


def test_ranking_order_is_stable():
    products = [
        solution("b", "Бета", 1200, 3_000_000),
        solution("a", "Альфа", 1200, 2_000_000),
        solution("c", "Гамма", None, 1_000_000),
    ]
    parameters = {"payload_kg": 800, "budget_mln_rub": 80}
    first, _ = rank_solutions(products, "warehouse", parameters, {"a", "b", "c"})
    second, _ = rank_solutions(list(reversed(products)), "warehouse", parameters, {"a", "b", "c"})
    assert [item["solution_id"] for item in first] == [item["solution_id"] for item in second]
    assert first[0]["solution_id"] == "a"


def test_known_robot_too_wide_is_excluded():
    item = score_solution(
        solution("wide", "Широкий", 1_000, width_m=1.2),
        "warehouse",
        {
            "payload_kg": 800,
            "budget_mln_rub": 80,
            "working_aisle_width_m": 1.4,
        },
        True,
    )

    assert item["eligible"] is False
    assert any(
        constraint["code"] == "aisle_width" and constraint["status"] == "failed"
        for constraint in item["constraints"]
    )


def test_draft_plan_route_stays_unknown():
    item = score_solution(
        solution("draft", "Draft", 1_000, width_m=0.8),
        "warehouse",
        {"payload_kg": 800, "budget_mln_rub": 80},
        True,
        {
            "width_m": 10,
            "height_m": 10,
            "review_status": "draft",
            "scale_status": "confirmed",
            "asset_id": "asset-1",
            "elements": [],
        },
    )

    route = next(
        constraint
        for constraint in item["constraints"]
        if constraint["code"] == "route_feasibility"
    )
    assert route["status"] == "unknown"
    assert item["requires_verification"] is True


def test_matching_model_weights_are_versioned_and_reproducible():
    assert MATCHING_MODEL_VERSION == "2026.09.2"
    assert WEIGHTS == {
        "functional": 0.25,
        "plan_feasibility": 0.25,
        "performance": 0.20,
        "economics": 0.15,
        "maturity": 0.10,
        "data_quality": 0.05,
    }
    item = solution("stable", "Стабильный", 1_000, width_m=0.8)
    parameters = {
        "payload_kg": 800,
        "budget_mln_rub": 80,
        "working_aisle_width_m": 2.0,
    }
    first = score_solution(item, "warehouse", parameters, True)
    second = score_solution(item, "warehouse", parameters, True)

    assert first == second
    assert set(first["contributions"]) == set(WEIGHTS)
