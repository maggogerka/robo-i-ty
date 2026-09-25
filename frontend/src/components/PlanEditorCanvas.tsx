import { useEffect, useMemo, useRef, useState } from "react";
import type { Stage as StageType } from "konva/lib/Stage";
import type { Transformer as TransformerType } from "konva/lib/shapes/Transformer";
import {
  Circle,
  Group,
  Image as KonvaImage,
  Layer,
  Line,
  Rect,
  Stage,
  Text,
  Transformer,
} from "react-konva";
import type { PlanElement, PlanElementKind, ProjectPlan } from "../types";

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

function useBackground(url: string | null) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!url) {
      setImage(null);
      return;
    }
    const next = new window.Image();
    next.onload = () => setImage(next);
    next.src = url;
    return () => {
      next.onload = null;
    };
  }, [url]);
  return image;
}

export type CalibrationPoint = { x_px: number; y_px: number };

export function PlanEditorCanvas({
  plan,
  backgroundUrl,
  selectedId,
  calibrationMode,
  calibrationPoints,
  onSelect,
  onChangeElement,
  onCalibrationPoint,
  onBackgroundSize,
}: {
  plan: ProjectPlan;
  backgroundUrl: string | null;
  selectedId: string | null;
  calibrationMode: boolean;
  calibrationPoints: CalibrationPoint[];
  onSelect: (id: string | null) => void;
  onChangeElement: (id: string, changes: Partial<PlanElement>) => void;
  onCalibrationPoint: (point: CalibrationPoint) => void;
  onBackgroundSize: (size: { width: number; height: number } | null) => void;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<StageType>(null);
  const transformerRef = useRef<TransformerType>(null);
  const [canvasWidth, setCanvasWidth] = useState(900);
  const [viewport, setViewport] = useState({ scale: 1, x: 0, y: 0 });
  const background = useBackground(backgroundUrl);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const update = () => setCanvasWidth(Math.max(320, host.clientWidth));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    onBackgroundSize(
      background
        ? { width: background.naturalWidth, height: background.naturalHeight }
        : null,
    );
  }, [background, onBackgroundSize]);

  useEffect(() => {
    const transformer = transformerRef.current;
    const stage = stageRef.current;
    if (!transformer || !stage) return;
    const node = selectedId ? stage.findOne(`#element-${selectedId}`) : null;
    transformer.nodes(node ? [node] : []);
    transformer.getLayer()?.batchDraw();
  }, [selectedId, plan.elements]);

  const scaleX = canvasWidth / plan.width_m;
  const canvasHeight = clamp(plan.height_m * scaleX, 320, 620);
  const scaleY = canvasHeight / plan.height_m;
  const grid = useMemo(
    () => ({
      vertical: Array.from(
        { length: Math.floor(plan.width_m / 5) + 1 },
        (_, index) => index * 5,
      ),
      horizontal: Array.from(
        { length: Math.floor(plan.height_m / 5) + 1 },
        (_, index) => index * 5,
      ),
    }),
    [plan.height_m, plan.width_m],
  );

  const handleCanvasPointer = () => {
    const stage = stageRef.current;
    if (!stage) return;
    if (!calibrationMode) {
      onSelect(null);
      return;
    }
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    const logical = stage.getAbsoluteTransform().copy().invert().point(pointer);
    const sourceWidth = background?.naturalWidth ?? canvasWidth;
    const sourceHeight = background?.naturalHeight ?? canvasHeight;
    onCalibrationPoint({
      x_px: clamp(logical.x / canvasWidth, 0, 1) * sourceWidth,
      y_px: clamp(logical.y / canvasHeight, 0, 1) * sourceHeight,
    });
  };

  return (
    <div className="plan-canvas editor-canvas" ref={hostRef}>
      <div className="canvas-controls">
        <button
          type="button"
          onClick={() => setViewport({ scale: 1, x: 0, y: 0 })}
        >
          Сбросить вид
        </button>
        <span>{Math.round(viewport.scale * 100)}%</span>
      </div>
      <Stage
        ref={stageRef}
        width={canvasWidth}
        height={canvasHeight}
        x={viewport.x}
        y={viewport.y}
        scaleX={viewport.scale}
        scaleY={viewport.scale}
        draggable={!calibrationMode}
        onMouseDown={(event) => {
          if (event.target === event.target.getStage()) handleCanvasPointer();
        }}
        onTouchStart={(event) => {
          if (event.target === event.target.getStage()) handleCanvasPointer();
        }}
        onDragEnd={(event) => {
          if (event.target === event.target.getStage()) {
            setViewport((current) => ({
              ...current,
              x: event.target.x(),
              y: event.target.y(),
            }));
          }
        }}
        onWheel={(event) => {
          event.evt.preventDefault();
          const stage = stageRef.current;
          const pointer = stage?.getPointerPosition();
          if (!stage || !pointer) return;
          const oldScale = viewport.scale;
          const direction = event.evt.deltaY > 0 ? -1 : 1;
          const nextScale = clamp(oldScale * (direction > 0 ? 1.12 : 0.88), 0.5, 4);
          const origin = {
            x: (pointer.x - viewport.x) / oldScale,
            y: (pointer.y - viewport.y) / oldScale,
          };
          setViewport({
            scale: nextScale,
            x: pointer.x - origin.x * nextScale,
            y: pointer.y - origin.y * nextScale,
          });
        }}
      >
        <Layer listening={false}>
          <Rect width={canvasWidth} height={canvasHeight} fill="#f9fbfb" />
          {background && (
            <KonvaImage
              image={background}
              width={canvasWidth}
              height={canvasHeight}
              opacity={0.34}
            />
          )}
          {grid.vertical.map((x) => (
            <Line
              key={`v-${x}`}
              points={[x * scaleX, 0, x * scaleX, canvasHeight]}
              stroke="#dbe5e7"
              strokeWidth={1}
            />
          ))}
          {grid.horizontal.map((y) => (
            <Line
              key={`h-${y}`}
              points={[0, y * scaleY, canvasWidth, y * scaleY]}
              stroke="#dbe5e7"
              strokeWidth={1}
            />
          ))}
          {calibrationPoints.map((point, index) => (
            <Circle
              key={`calibration-${index}`}
              x={(point.x_px / (background?.naturalWidth ?? canvasWidth)) * canvasWidth}
              y={(point.y_px / (background?.naturalHeight ?? canvasHeight)) * canvasHeight}
              radius={7}
              fill="#f15b3a"
              stroke="#fff"
              strokeWidth={2}
            />
          ))}
        </Layer>
        <Layer>
          {plan.elements.map((item) => {
            const width = item.width_m * scaleX;
            const height = item.height_m * scaleY;
            const colors = palette[item.kind];
            const lowConfidence =
              item.confidence < 0.7 || item.review_status === "needs_review";
            return (
              <Group
                id={`element-${item.id}`}
                key={item.id}
                x={item.x_m * scaleX}
                y={item.y_m * scaleY}
                draggable={!calibrationMode}
                dragBoundFunc={(position) => ({
                  x: clamp(position.x, 0, canvasWidth - width),
                  y: clamp(position.y, 0, canvasHeight - height),
                })}
                onClick={() => onSelect(item.id)}
                onTap={() => onSelect(item.id)}
                onDragEnd={(event) =>
                  onChangeElement(item.id, {
                    x_m: Math.round((event.target.x() / scaleX) * 10) / 10,
                    y_m: Math.round((event.target.y() / scaleY) * 10) / 10,
                  })
                }
                onTransformEnd={(event) => {
                  const node = event.target;
                  const nextWidth = clamp(item.width_m * node.scaleX(), 0.1, plan.width_m);
                  const nextHeight = clamp(
                    item.height_m * node.scaleY(),
                    0.1,
                    plan.height_m,
                  );
                  node.scaleX(1);
                  node.scaleY(1);
                  onChangeElement(item.id, {
                    x_m: clamp(node.x() / scaleX, 0, plan.width_m - nextWidth),
                    y_m: clamp(node.y() / scaleY, 0, plan.height_m - nextHeight),
                    width_m: nextWidth,
                    height_m: nextHeight,
                  });
                }}
              >
                <Rect
                  width={width}
                  height={height}
                  fill={colors.fill}
                  opacity={item.kind.endsWith("zone") ? 0.48 : 0.86}
                  stroke={
                    selectedId === item.id
                      ? "#043d58"
                      : lowConfidence
                        ? "#db4b2f"
                        : colors.stroke
                  }
                  strokeWidth={selectedId === item.id ? 3 : 1.5}
                  dash={lowConfidence ? [7, 4] : undefined}
                  cornerRadius={Math.min(7, width / 8, height / 8)}
                />
                <Text
                  text={item.label}
                  width={width}
                  height={height}
                  padding={Math.min(7, width / 10)}
                  align="center"
                  verticalAlign="middle"
                  fill="#203f4d"
                  fontSize={clamp(Math.min(width, height) / 5, 8, 13)}
                  fontStyle="bold"
                  ellipsis
                />
              </Group>
            );
          })}
          <Transformer
            ref={transformerRef}
            rotateEnabled={false}
            flipEnabled={false}
            enabledAnchors={[
              "top-left",
              "top-right",
              "bottom-left",
              "bottom-right",
            ]}
            boundBoxFunc={(oldBox, newBox) =>
              newBox.width < 8 || newBox.height < 8 ? oldBox : newBox
            }
          />
        </Layer>
      </Stage>
      <p className="canvas-note">
        Колесо — масштаб · перетаскивание поля — панорама · рамка — изменение размера
      </p>
    </div>
  );
}

