from app.simulation import (
    Point,
    Rect,
    SimulationInputs,
    build_astar_route,
    build_route,
    calculate_simulation,
)


def test_simulation_is_reproducible_and_uses_explicit_units():
    inputs = SimulationInputs(
        daily_tasks=1_000,
        operating_hours_per_day=16,
        robot_speed_m_s=1.2,
        handling_time_seconds=35,
        availability_percent=92,
    )
    route = [Point(2, 2), Point(30, 2), Point(30, 20)]

    first = calculate_simulation(inputs, route)
    second = calculate_simulation(inputs, route)

    assert first == second
    assert first["route_distance_m"] == 46
    assert first["recommended_robots"] > 0
    assert first["completed_tasks_day"] <= inputs.daily_tasks


def test_route_reports_collision_instead_of_treating_it_as_passed():
    obstacles = [Rect(x=4, y=0, width=2, height=9), Rect(x=0, y=4, width=9, height=2)]

    route, warnings = build_route(Point(1, 1), Point(8, 8), obstacles)

    assert len(route) == 3
    assert warnings
    assert "пересекает" in warnings[0]


def test_plan_api_validates_saves_and_runs(client, auth):
    project = client.post("/api/v1/projects/demo", headers=auth, json={}).json()
    plan_url = f"/api/v1/projects/{project['id']}/plan"
    simulation_url = f"/api/v1/projects/{project['id']}/simulation"

    initial = client.get(plan_url, headers=auth)
    assert initial.status_code == 200
    assert initial.json()["revision"] == 0

    plan = initial.json()
    plan.pop("revision")
    plan.pop("source_status")
    saved = client.put(plan_url, headers=auth, json=plan)
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1

    resaved = client.put(plan_url, headers=auth, json=plan)
    assert resaved.status_code == 200
    assert resaved.json()["revision"] == 2
    assert len(resaved.json()["elements"]) == len(plan["elements"])

    invalid = {**plan, "unexpected": "blocked"}
    assert client.put(plan_url, headers=auth, json=invalid).status_code == 422

    first = client.post(simulation_url, headers=auth, json={})
    second = client.post(simulation_url, headers=auth, json={})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["model_version"] == "2026.09.2"
    assert first.json()["plan_revision"] == 2
    for key in (
        "recommended_robots",
        "route_distance_m",
        "cycle_time_seconds",
        "throughput_tasks_hour",
        "utilization_percent",
    ):
        assert first.json()[key] == second.json()[key]
    assert all(item["status"] == "assumed" for item in first.json()["assumptions"])
    assert not any("пересекает препятствия" in warning for warning in first.json()["warnings"])
    economics = client.post(f"/api/v1/projects/{project['id']}/economics", headers=auth, json={})
    assert economics.status_code == 200
    assert economics.json()["model_version"] == "2026.09.2"
    assert economics.json()["fleet_basis"] == "latest_simulation"
    assert economics.json()["required_robots"] >= first.json()["recommended_robots"]


def test_astar_route_is_deterministic_and_avoids_inflated_obstacles():
    start = Point(1, 1)
    finish = Point(9, 1)
    obstacles = [Rect(x=4, y=0, width=2, height=6)]

    first, first_warnings = build_astar_route(
        start,
        finish,
        obstacles,
        width_m=10,
        height_m=10,
        clearance_m=0.5,
        cell_size_m=0.5,
    )
    second, second_warnings = build_astar_route(
        start,
        finish,
        obstacles,
        width_m=10,
        height_m=10,
        clearance_m=0.5,
        cell_size_m=0.5,
    )

    assert first == second
    assert first_warnings == second_warnings
    assert first[0] == start
    assert first[-1] == finish
    assert max(point.y for point in first) > 6.5


def test_astar_does_not_turn_missing_route_into_a_pass():
    route, warnings = build_astar_route(
        Point(1, 1),
        Point(9, 1),
        [Rect(x=4, y=0, width=2, height=10)],
        width_m=10,
        height_m=10,
        clearance_m=0.5,
        cell_size_m=0.5,
    )

    assert route == []
    assert warnings
    assert "не найден" in warnings[-1]


def test_confirmed_plan_rejects_blocked_route(client, auth):
    project = client.post("/api/v1/projects/demo", headers=auth, json={}).json()
    plan_url = f"/api/v1/projects/{project['id']}/plan"
    plan = client.get(plan_url, headers=auth).json()
    plan.pop("revision")
    plan.pop("source_status")
    plan["review_status"] = "confirmed"
    plan["elements"].append(
        {
            "id": "wall-blocking",
            "kind": "wall",
            "label": "Непроходимая стена",
            "x_m": 28,
            "y_m": 0,
            "width_m": 4,
            "height_m": plan["height_m"],
            "rotation_deg": 0,
            "confidence": 1,
            "source": "manual",
            "review_status": "confirmed",
            "source_region": None,
        }
    )

    response = client.put(plan_url, headers=auth, json=plan)

    assert response.status_code == 422
    assert "маршрут" in response.json()["detail"].lower()
