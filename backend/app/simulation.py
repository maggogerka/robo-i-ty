from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil, hypot

SIMULATION_MODEL_VERSION = "2026.09.1"


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class SimulationInputs:
    daily_tasks: float
    operating_hours_per_day: float
    robot_speed_m_s: float
    handling_time_seconds: float
    availability_percent: float
    robot_count: int | None = None


def polyline_length(points: Iterable[Point]) -> float:
    items = list(points)
    return sum(hypot(b.x - a.x, b.y - a.y) for a, b in zip(items, items[1:], strict=False))


def segment_crosses_rect(a: Point, b: Point, rect: Rect) -> bool:
    """Проверяет пересечение осевого сегмента с прямоугольником без вращения."""

    if a.x == b.x:
        return (
            rect.x < a.x < rect.x + rect.width
            and max(a.y, b.y) > rect.y
            and min(a.y, b.y) < rect.y + rect.height
        )
    if a.y == b.y:
        return (
            rect.y < a.y < rect.y + rect.height
            and max(a.x, b.x) > rect.x
            and min(a.x, b.x) < rect.x + rect.width
        )
    return False


def build_route(
    start: Point, finish: Point, obstacles: list[Rect]
) -> tuple[list[Point], list[str]]:
    """Строит воспроизводимый ортогональный маршрут и честно отмечает коллизии."""

    candidates = [
        [start, Point(finish.x, start.y), finish],
        [start, Point(start.x, finish.y), finish],
    ]

    def collisions(route: list[Point]) -> int:
        return sum(
            segment_crosses_rect(a, b, obstacle)
            for a, b in zip(route, route[1:], strict=False)
            for obstacle in obstacles
        )

    route = min(candidates, key=lambda item: (collisions(item), polyline_length(item)))
    collision_count = collisions(route)
    warnings = []
    if collision_count:
        warnings.append(
            f"Маршрут пересекает препятствия: {collision_count}. Требуется скорректировать план."
        )
    return route, warnings


def calculate_simulation(inputs: SimulationInputs, route_points: list[Point]) -> dict:
    if inputs.daily_tasks <= 0:
        raise ValueError("Суточное число заданий должно быть больше нуля")
    if inputs.operating_hours_per_day <= 0:
        raise ValueError("Рабочее время должно быть больше нуля")
    if len(route_points) < 2:
        raise ValueError("Маршрут должен содержать минимум две точки")

    one_way_distance_m = polyline_length(route_points)
    if one_way_distance_m <= 0:
        raise ValueError("Длина маршрута должна быть больше нуля")

    cycle_distance_m = one_way_distance_m * 2
    cycle_time_seconds = (
        cycle_distance_m / inputs.robot_speed_m_s + inputs.handling_time_seconds * 2
    )
    availability = inputs.availability_percent / 100
    per_robot_tasks_hour = 3600 / cycle_time_seconds * availability
    demand_tasks_hour = inputs.daily_tasks / inputs.operating_hours_per_day
    recommended_robots = max(1, ceil(demand_tasks_hour / per_robot_tasks_hour))
    robot_count = inputs.robot_count or recommended_robots
    capacity_tasks_hour = robot_count * per_robot_tasks_hour
    throughput_tasks_hour = min(demand_tasks_hour, capacity_tasks_hour)
    completed_tasks_day = throughput_tasks_hour * inputs.operating_hours_per_day
    utilization_percent = min(100.0, demand_tasks_hour / capacity_tasks_hour * 100)
    capacity_gap_tasks_day = max(0.0, inputs.daily_tasks - completed_tasks_day)

    warnings = []
    if robot_count < recommended_robots:
        warnings.append(f"Парка недостаточно: требуется не менее {recommended_robots} роботов.")
    if utilization_percent > 85:
        warnings.append("Загрузка выше 85%: рекомендуется резерв пропускной способности.")

    return {
        "model_version": SIMULATION_MODEL_VERSION,
        "robot_count": robot_count,
        "recommended_robots": recommended_robots,
        "route_distance_m": round(one_way_distance_m, 2),
        "cycle_distance_m": round(cycle_distance_m, 2),
        "cycle_time_seconds": round(cycle_time_seconds, 2),
        "throughput_tasks_hour": round(throughput_tasks_hour, 2),
        "capacity_tasks_hour": round(capacity_tasks_hour, 2),
        "completed_tasks_day": round(completed_tasks_day, 2),
        "capacity_gap_tasks_day": round(capacity_gap_tasks_day, 2),
        "utilization_percent": round(utilization_percent, 2),
        "route_points": [{"x_m": point.x, "y_m": point.y} for point in route_points],
        "warnings": warnings,
    }
