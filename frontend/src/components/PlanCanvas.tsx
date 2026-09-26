import { useEffect, useMemo, useRef, useState } from "react";
import { Circle, Group, Layer, Line, Rect, Stage, Text } from "react-konva";
import type { PlanElement, PlanElementKind, ProjectPlan, SimulationResult } from "../types";

const palette: Record<PlanElementKind, { fill: string; stroke: string }> = {
  wall: { fill: "#76858c", stroke: "#34454d" },
  door: { fill: "#c4e0da", stroke: "#16705a" },
  storage: { fill: "#d9e5e8", stroke: "#6e8792" },
  obstacle: { fill: "#f4d9d1", stroke: "#bd624d" },
  work_zone: { fill: "#dcefdc", stroke: "#4d8750" },
  restricted_zone: { fill: "#f8d4d4", stroke: "#b73d3d" },
  pickup: { fill: "#d9f1e6", stroke: "#198461" },
  dropoff: { fill: "#d9eaf5", stroke: "#24739a" },
  charger: { fill: "#fff0c7", stroke: "#af7917" },
};

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function positionOnRoute(points: { x_m: number; y_m: number }[], progress: number) {
  if (points.length < 2) return points[0] ?? { x_m: 0, y_m: 0 };
  const lengths = points.slice(1).map((point, index) =>
    Math.hypot(point.x_m - points[index].x_m, point.y_m - points[index].y_m),
  );
  const total = lengths.reduce((sum, value) => sum + value, 0);
  let target = total * progress;
  for (let index = 0; index < lengths.length; index += 1) {
    if (target <= lengths[index]) {
      const ratio = lengths[index] === 0 ? 0 : target / lengths[index];
      return {
        x_m: points[index].x_m + (points[index + 1].x_m - points[index].x_m) * ratio,
        y_m: points[index].y_m + (points[index + 1].y_m - points[index].y_m) * ratio,
      };
    }
    target -= lengths[index];
  }
  return points.at(-1) ?? points[0];
}

export function PlanCanvas({
  plan,
  selectedId,
  onSelect,
  onMove,
  result,
  running,
}: {
  plan: ProjectPlan;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMove: (id: string, x: number, y: number) => void;
  result: SimulationResult | null;
  running: boolean;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [canvasWidth, setCanvasWidth] = useState(900);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const update = () => setCanvasWidth(Math.max(300, host.clientWidth));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!running) return;
    let frame = 0;
    const startedAt = performance.now();
    const animate = (now: number) => {
      setProgress(((now - startedAt) % 8_000) / 8_000);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [running]);

  const scale = canvasWidth / plan.width_m;
  const canvasHeight = clamp(plan.height_m * scale, 300, 560);
  const scaleY = canvasHeight / plan.height_m;
  const grid = useMemo(() => {
    const vertical = Array.from({ length: Math.floor(plan.width_m / 5) + 1 }, (_, i) => i * 5);
    const horizontal = Array.from({ length: Math.floor(plan.height_m / 5) + 1 }, (_, i) => i * 5);
    return { vertical, horizontal };
  }, [plan.height_m, plan.width_m]);
  const route = result?.route_points ?? [];
  const routePixels = route.flatMap((point) => [point.x_m * scale, point.y_m * scaleY]);
  const robots = Math.min(result?.robot_count ?? 0, 12);

  return (
    <div
      className="plan-canvas"
      ref={hostRef}
      role="img"
      aria-label={`План ${plan.width_m} на ${plan.height_m} метров. Элементов: ${plan.elements.length}`}
    >
      <Stage
        width={canvasWidth}
        height={canvasHeight}
        onMouseDown={(event) => {
          if (event.target === event.target.getStage()) onSelect(null);
        }}
        onTouchStart={(event) => {
          if (event.target === event.target.getStage()) onSelect(null);
        }}
      >
        <Layer listening={false}>
          <Rect width={canvasWidth} height={canvasHeight} fill="#f9fbfb" />
          {grid.vertical.map((x) => (
            <Line
              key={`v-${x}`}
              points={[x * scale, 0, x * scale, canvasHeight]}
              stroke="#e4ecee"
              strokeWidth={1}
            />
          ))}
          {grid.horizontal.map((y) => (
            <Line
              key={`h-${y}`}
              points={[0, y * scaleY, canvasWidth, y * scaleY]}
              stroke="#e4ecee"
              strokeWidth={1}
            />
          ))}
          {routePixels.length >= 4 && (
            <Line
              points={routePixels}
              stroke="#078f86"
              strokeWidth={4}
              dash={[10, 8]}
              lineCap="round"
              lineJoin="round"
            />
          )}
        </Layer>
        <Layer>
          {plan.elements.map((item) => (
            <PlanShape
              key={item.id}
              item={item}
              scaleX={scale}
              scaleY={scaleY}
              plan={plan}
              selected={selectedId === item.id}
              disabled={running}
              onSelect={() => onSelect(item.id)}
              onMove={(x, y) => onMove(item.id, x, y)}
            />
          ))}
          {Array.from({ length: robots }, (_, index) => {
            const shifted = (progress + index / Math.max(robots, 1)) % 1;
            const thereAndBack = shifted <= 0.5 ? shifted * 2 : (1 - shifted) * 2;
            const position = positionOnRoute(route, thereAndBack);
            return (
              <Circle
                key={`robot-${index}`}
                x={position.x_m * scale}
                y={position.y_m * scaleY}
                radius={Math.max(5, Math.min(scale, scaleY) * 0.7)}
                fill="#073b5c"
                stroke="#44d9cc"
                strokeWidth={2}
                shadowColor="#12394b"
                shadowBlur={6}
                shadowOpacity={0.22}
                listening={false}
              />
            );
          })}
        </Layer>
      </Stage>
      {result && result.robot_count > 12 && (
        <span className="canvas-note">На схеме показано 12 из {result.robot_count} роботов</span>
      )}
    </div>
  );
}

function PlanShape({
  item,
  scaleX,
  scaleY,
  plan,
  selected,
  disabled,
  onSelect,
  onMove,
}: {
  item: PlanElement;
  scaleX: number;
  scaleY: number;
  plan: ProjectPlan;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
  onMove: (x: number, y: number) => void;
}) {
  const colors = palette[item.kind];
  const width = item.width_m * scaleX;
  const height = item.height_m * scaleY;
  return (
    <Group
      x={item.x_m * scaleX}
      y={item.y_m * scaleY}
      draggable={!disabled}
      dragBoundFunc={(position) => ({
        x: clamp(position.x, 0, plan.width_m * scaleX - width),
        y: clamp(position.y, 0, plan.height_m * scaleY - height),
      })}
      onClick={onSelect}
      onTap={onSelect}
      onDragEnd={(event) => {
        const x = Math.round((event.target.x() / scaleX) * 2) / 2;
        const y = Math.round((event.target.y() / scaleY) * 2) / 2;
        onMove(x, y);
      }}
    >
      <Rect
        width={width}
        height={height}
        fill={colors.fill}
        stroke={selected ? "#043d58" : colors.stroke}
        strokeWidth={selected ? 3 : 1.5}
        cornerRadius={Math.min(8, width / 8, height / 8)}
        shadowColor="#274b5a"
        shadowBlur={selected ? 10 : 0}
        shadowOpacity={0.18}
      />
      <Text
        text={item.label}
        width={width}
        height={height}
        padding={Math.min(8, width / 10)}
        align="center"
        verticalAlign="middle"
        fill="#274452"
        fontSize={clamp(Math.min(width, height) / 5, 9, 13)}
        fontStyle="bold"
        ellipsis
      />
    </Group>
  );
}
