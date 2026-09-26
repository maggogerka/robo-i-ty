from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from heapq import heappop, heappush
from math import ceil, floor, hypot, sqrt

SIMULATION_MODEL_VERSION = "2026.09.2"
MAX_GRID_NODES = 120_000


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
    """Совместимый простой маршрут; основной расчёт использует build_astar_route."""

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


def _inflate(rect: Rect, clearance_m: float) -> Rect:
    return Rect(
        x=rect.x - clearance_m,
        y=rect.y - clearance_m,
        width=rect.width + clearance_m * 2,
        height=rect.height + clearance_m * 2,
    )


def _inside(point: Point, rect: Rect) -> bool:
    return rect.x <= point.x <= rect.x + rect.width and rect.y <= point.y <= rect.y + rect.height


def _simplify_route(points: list[Point]) -> list[Point]:
    if len(points) < 3:
        return points
    simplified = [points[0]]
    for current, following in zip(points[1:-1], points[2:], strict=False):
        previous = simplified[-1]
        cross = (current.x - previous.x) * (following.y - current.y) - (current.y - previous.y) * (
            following.x - current.x
        )
        if abs(cross) > 1e-9:
            simplified.append(current)
    simplified.append(points[-1])
    return simplified


def build_astar_route(
    start: Point,
    finish: Point,
    obstacles: list[Rect],
    *,
    width_m: float,
    height_m: float,
    clearance_m: float,
    cell_size_m: float = 0.5,
) -> tuple[list[Point], list[str]]:
    """Строит воспроизводимый 8-связный маршрут с учётом габарита робота."""

    if width_m <= 0 or height_m <= 0 or cell_size_m <= 0 or clearance_m < 0:
        raise ValueError("Размеры плана, ячейки и запас безопасности должны быть корректными")
    if not (0 <= start.x <= width_m and 0 <= start.y <= height_m):
        raise ValueError("Точка забора находится за границами плана")
    if not (0 <= finish.x <= width_m and 0 <= finish.y <= height_m):
        raise ValueError("Точка доставки находится за границами плана")

    effective_cell = max(cell_size_m, sqrt(width_m * height_m / MAX_GRID_NODES))
    columns = floor(width_m / effective_cell) + 1
    rows = floor(height_m / effective_cell) + 1
    warnings: list[str] = []
    if effective_cell > cell_size_m + 1e-9:
        warnings.append(
            f"Шаг сетки A* увеличен до {effective_cell:.3f} м для ограничения ресурсоёмкости."
        )

    inflated = [_inflate(rect, clearance_m) for rect in obstacles]
    blocked = bytearray(columns * rows)

    def node_point(node: tuple[int, int]) -> Point:
        return Point(node[0] * effective_cell, node[1] * effective_cell)

    def node_index(node: tuple[int, int]) -> int:
        return node[1] * columns + node[0]

    minimum_x = ceil(clearance_m / effective_cell)
    minimum_y = ceil(clearance_m / effective_cell)
    maximum_x = floor((width_m - clearance_m) / effective_cell)
    maximum_y = floor((height_m - clearance_m) / effective_cell)
    if minimum_x > maximum_x or minimum_y > maximum_y:
        return [], ["Габарит робота с запасом безопасности не помещается в границы плана."]

    for y_index in range(rows):
        for x_index in range(columns):
            if not (minimum_x <= x_index <= maximum_x and minimum_y <= y_index <= maximum_y):
                blocked[node_index((x_index, y_index))] = 1

    for rect in inflated:
        from_x = max(0, ceil(rect.x / effective_cell))
        to_x = min(columns - 1, floor((rect.x + rect.width) / effective_cell))
        from_y = max(0, ceil(rect.y / effective_cell))
        to_y = min(rows - 1, floor((rect.y + rect.height) / effective_cell))
        for y_index in range(from_y, to_y + 1):
            offset = y_index * columns
            for x_index in range(from_x, to_x + 1):
                blocked[offset + x_index] = 1

    if any(_inside(start, rect) for rect in inflated):
        return [], ["Точка забора пересекает препятствие с учётом габарита робота."]
    if any(_inside(finish, rect) for rect in inflated):
        return [], ["Точка доставки пересекает препятствие с учётом габарита робота."]

    def segment_clear(origin: Point, target: Point) -> bool:
        distance = hypot(target.x - origin.x, target.y - origin.y)
        sample_count = max(1, ceil(distance / (effective_cell / 2)))
        for sample in range(sample_count + 1):
            ratio = sample / sample_count
            point = Point(
                origin.x + (target.x - origin.x) * ratio,
                origin.y + (target.y - origin.y) * ratio,
            )
            if not (
                clearance_m <= point.x <= width_m - clearance_m
                and clearance_m <= point.y <= height_m - clearance_m
            ):
                return False
            if any(_inside(point, rect) for rect in inflated):
                return False
        return True

    def nearest_node(point: Point) -> tuple[int, int] | None:
        candidates: list[tuple[float, int, int]] = []
        for y_index in range(minimum_y, maximum_y + 1):
            for x_index in range(minimum_x, maximum_x + 1):
                node = (x_index, y_index)
                if blocked[node_index(node)]:
                    continue
                target = node_point(node)
                distance = (target.x - point.x) ** 2 + (target.y - point.y) ** 2
                candidates.append((distance, y_index, x_index))
        candidates.sort()
        for _, y_index, x_index in candidates:
            node = (x_index, y_index)
            if segment_clear(point, node_point(node)):
                return node
        return None

    start_node = nearest_node(start)
    finish_node = nearest_node(finish)
    if start_node is None or finish_node is None:
        return [], ["Не удалось связать контрольные точки с безопасной маршрутной сеткой."]

    directions = (
        (1, 0, 1.0),
        (0, 1, 1.0),
        (-1, 0, 1.0),
        (0, -1, 1.0),
        (1, 1, sqrt(2)),
        (-1, 1, sqrt(2)),
        (-1, -1, sqrt(2)),
        (1, -1, sqrt(2)),
    )

    def heuristic(node: tuple[int, int]) -> float:
        dx = abs(finish_node[0] - node[0])
        dy = abs(finish_node[1] - node[1])
        return max(dx, dy) + (sqrt(2) - 1) * min(dx, dy)

    frontier: list[tuple[float, float, int, int]] = []
    heappush(frontier, (heuristic(start_node), 0.0, start_node[1], start_node[0]))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    cost_so_far = {start_node: 0.0}

    while frontier:
        _, current_cost, current_y, current_x = heappop(frontier)
        current = (current_x, current_y)
        if current_cost > cost_so_far.get(current, float("inf")) + 1e-12:
            continue
        if current == finish_node:
            break
        for delta_x, delta_y, movement_cost in directions:
            neighbour = (current_x + delta_x, current_y + delta_y)
            if not (0 <= neighbour[0] < columns and 0 <= neighbour[1] < rows):
                continue
            if blocked[node_index(neighbour)]:
                continue
            if delta_x and delta_y:
                first_side = (current_x + delta_x, current_y)
                second_side = (current_x, current_y + delta_y)
                if blocked[node_index(first_side)] or blocked[node_index(second_side)]:
                    continue
            next_cost = current_cost + movement_cost
            if next_cost + 1e-12 >= cost_so_far.get(neighbour, float("inf")):
                continue
            cost_so_far[neighbour] = next_cost
            came_from[neighbour] = current
            priority = next_cost + heuristic(neighbour)
            heappush(frontier, (priority, next_cost, neighbour[1], neighbour[0]))

    if finish_node not in cost_so_far:
        return [], warnings + ["Безопасный маршрут между точками забора и доставки не найден."]

    nodes = [finish_node]
    while nodes[-1] != start_node:
        nodes.append(came_from[nodes[-1]])
    nodes.reverse()
    route = [node_point(node) for node in nodes]
    if route[0] != start:
        route.insert(0, start)
    if route[-1] != finish:
        route.append(finish)
    return _simplify_route(route), warnings


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
