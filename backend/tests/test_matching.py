from app.matching import rank_solutions, score_solution
from app.models import RobotSolution


def solution(id_: str, name: str, payload: float | None, price: float = 2_000_000):
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
