import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Ban,
  Bot,
  Box,
  Gauge,
  Info,
  MapPin,
  Pause,
  Play,
  Plus,
  Route,
  Save,
  Timer,
  Trash2,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { PlanCanvas } from "../components/PlanCanvas";
import { ProjectSteps } from "../components/ProjectSteps";
import { Badge, Button, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import type {
  PlanElement,
  PlanElementKind,
  ProjectPlan,
  SimulationResult,
} from "../types";

const labels: Record<PlanElementKind, string> = {
  wall: "Стена",
  door: "Дверь",
  storage: "Стеллаж",
  obstacle: "Препятствие",
  work_zone: "Рабочая зона",
  restricted_zone: "Запретная зона",
  pickup: "Забор",
  dropoff: "Доставка",
  charger: "Зарядка",
};

const number = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

function planForApi(plan: ProjectPlan) {
  return {
    name: plan.name,
    width_m: plan.width_m,
    height_m: plan.height_m,
    asset_id: plan.asset_id,
    scale_m_per_px: plan.scale_m_per_px,
    scale_status: plan.scale_status,
    review_status: plan.review_status,
    provider_key: plan.provider_key,
    elements: plan.elements,
  };
}

export function SimulationPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [plan, setPlan] = useState<ProjectPlan | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [robotCount, setRobotCount] = useState<number | "">("");
  const [speed, setSpeed] = useState(1.2);
  const [handlingTime, setHandlingTime] = useState(35);
  const [availability, setAvailability] = useState(92);

  const planQuery = useQuery({
    queryKey: ["plan", id],
    queryFn: () => api<ProjectPlan>(`/projects/${id}/plan`),
    enabled: Boolean(id),
  });
  useEffect(() => {
    if (planQuery.data) setPlan(planQuery.data);
  }, [planQuery.data]);

  const save = useMutation({
    mutationFn: (current: ProjectPlan) =>
      api<ProjectPlan>(`/projects/${id}/plan`, {
        method: "PUT",
        body: JSON.stringify(planForApi(current)),
      }),
    onSuccess: (saved) => {
      setPlan(saved);
      queryClient.setQueryData(["plan", id], saved);
      setMessage(`План сохранён · ревизия ${saved.revision}`);
    },
  });

  const simulation = useMutation({
    mutationFn: async (current: ProjectPlan) => {
      const saved = await api<ProjectPlan>(`/projects/${id}/plan`, {
        method: "PUT",
        body: JSON.stringify(planForApi(current)),
      });
      const calculated = await api<SimulationResult>(`/projects/${id}/simulation`, {
        method: "POST",
        body: JSON.stringify({
          robot_count: robotCount === "" ? null : robotCount,
          robot_speed_m_s: speed,
          handling_time_seconds: handlingTime,
          availability_percent: availability,
        }),
      });
      return { saved, calculated };
    },
    onSuccess: ({ saved, calculated }) => {
      setPlan(saved);
      queryClient.setQueryData(["plan", id], saved);
      setResult(calculated);
      setRobotCount(calculated.robot_count);
      setRunning(true);
      setMessage(`Расчёт выполнен · запуск ${calculated.run_id.slice(0, 8)}`);
    },
  });

  const selected = useMemo(
    () => plan?.elements.find((item) => item.id === selectedId) ?? null,
    [plan, selectedId],
  );

  const updateElement = (elementId: string, changes: Partial<PlanElement>) => {
    setPlan((current) =>
      current
        ? {
            ...current,
            elements: current.elements.map((item) =>
              item.id === elementId ? { ...item, ...changes } : item,
            ),
          }
        : current,
    );
    setResult(null);
    setRunning(false);
    setMessage(null);
  };

  const addElement = (kind: PlanElementKind) => {
    if (!plan || plan.elements.length >= 250) return;
    const ordinal = plan.elements.filter((item) => item.kind === kind).length + 1;
    const width = kind === "charger" ? 6 : kind === "pickup" || kind === "dropoff" ? 8 : 7;
    const height = kind === "charger" ? 5 : kind === "pickup" || kind === "dropoff" ? 8 : 10;
    const element: PlanElement = {
      id: `${kind}-${Date.now().toString(36)}`,
      kind,
      label: `${labels[kind]} ${ordinal}`,
      x_m: Math.min(plan.width_m - width, 4 + (ordinal % 5) * 3),
      y_m: Math.min(plan.height_m - height, 4 + (ordinal % 4) * 3),
      width_m: width,
      height_m: height,
      rotation_deg: 0,
      confidence: 1,
      source: "manual",
      review_status: "reviewed",
      source_region: null,
    };
    setPlan({ ...plan, elements: [...plan.elements, element] });
    setSelectedId(element.id);
    setResult(null);
    setRunning(false);
  };

  const removeSelected = () => {
    if (!plan || !selected) return;
    if (
      (selected.kind === "pickup" || selected.kind === "dropoff") &&
      plan.elements.filter((item) => item.kind === selected.kind).length === 1
    ) {
      setMessage(`Нельзя удалить последнюю зону «${labels[selected.kind]}»`);
      return;
    }
    setPlan({ ...plan, elements: plan.elements.filter((item) => item.id !== selected.id) });
    setSelectedId(null);
    setResult(null);
    setRunning(false);
  };

  if (planQuery.isPending || !plan) {
    return <Loading label="Загружаем план объекта" />;
  }
  if (planQuery.error) {
    return <ErrorState message={planQuery.error.message} />;
  }

  const pending = save.isPending || simulation.isPending;
  const requestError = save.error?.message ?? simulation.error?.message;

  return (
    <section className="page page-wide project-page simulation-page">
      <ProjectSteps projectId={id} />
      <div className="page-header">
        <div>
          <p className="section-kicker">Модель 2026.09.1 · детерминированный расчёт</p>
          <h1>2D-план и симуляция</h1>
          <p>Перемещайте зоны, проверяйте маршрут и пропускную способность парка.</p>
        </div>
        <div className="quality-box">
          <span>План</span>
          <b>Ревизия {plan.revision || "не сохранена"}</b>
          <small>{plan.elements.length} элементов · {plan.width_m} × {plan.height_m} м</small>
        </div>
      </div>

      <div className="simulation-toolbar" aria-label="Инструменты плана">
        <span>Добавить:</span>
        <Button onClick={() => addElement("storage")}><Box size={16} /> Стеллаж</Button>
        <Button onClick={() => addElement("obstacle")}><Ban size={16} /> Препятствие</Button>
        <Button onClick={() => addElement("pickup")}><MapPin size={16} /> Забор</Button>
        <Button onClick={() => addElement("dropoff")}><Plus size={16} /> Доставка</Button>
        <Button onClick={() => addElement("charger")}><Zap size={16} /> Зарядка</Button>
        <Button
          className="button-danger"
          disabled={!selected}
          onClick={removeSelected}
        ><Trash2 size={16} /> Удалить</Button>
      </div>

      <div className="simulation-layout">
        <div>
          <PlanCanvas
            plan={plan}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onMove={(elementId, x, y) => updateElement(elementId, { x_m: x, y_m: y })}
            result={result}
            running={running}
          />
          <div className="canvas-legend">
            {(Object.keys(labels) as PlanElementKind[]).map((kind) => (
              <span key={kind}><i className={`legend-${kind}`} />{labels[kind]}</span>
            ))}
            <small>Сетка 5 м · координаты округляются до 0,5 м</small>
          </div>
        </div>

        <aside className="simulation-panel">
          <div className="panel-section">
            <p className="section-kicker">Параметры запуска</p>
            <label className="compact-field">
              <span>Роботов в парке</span>
              <input
                type="number"
                min="1"
                max="500"
                placeholder="Автоматически"
                value={robotCount}
                onChange={(event) =>
                  setRobotCount(event.target.value === "" ? "" : Number(event.target.value))
                }
              />
            </label>
            <label className="compact-field"><span>Скорость, м/с</span><input type="number" min="0.1" max="5" step="0.1" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} /></label>
            <label className="compact-field"><span>Обработка, с/операцию</span><input type="number" min="0" max="3600" value={handlingTime} onChange={(event) => setHandlingTime(Number(event.target.value))} /></label>
            <label className="compact-field"><span>Доступность, %</span><input type="number" min="1" max="100" value={availability} onChange={(event) => setAvailability(Number(event.target.value))} /></label>
          </div>

          {selected && (
            <div className="panel-section selected-editor">
              <div className="selected-title"><span>Выбран объект</span><Badge tone="source">{labels[selected.kind]}</Badge></div>
              <label className="compact-field"><span>Название</span><input value={selected.label} maxLength={120} onChange={(event) => updateElement(selected.id, { label: event.target.value })} /></label>
              <div className="coordinate-grid">
                {(["x_m", "y_m", "width_m", "height_m"] as const).map((key) => (
                  <label className="compact-field" key={key}>
                    <span>{{ x_m: "X, м", y_m: "Y, м", width_m: "Ширина, м", height_m: "Высота, м" }[key]}</span>
                    <input
                      type="number"
                      min={key === "x_m" || key === "y_m" ? 0 : 0.5}
                      step="0.5"
                      value={selected[key]}
                      onChange={(event) => updateElement(selected.id, { [key]: Number(event.target.value) })}
                    />
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="simulation-actions">
            <Button className="button-secondary" disabled={pending} onClick={() => save.mutate(plan)}><Save size={17} /> Сохранить</Button>
            <Button className="button-primary" disabled={pending} onClick={() => simulation.mutate(plan)}><Play size={17} /> {simulation.isPending ? "Считаем…" : "Запустить"}</Button>
            {result && <Button className="button-quiet" onClick={() => setRunning((value) => !value)}>{running ? <Pause size={17} /> : <Play size={17} />}{running ? "Пауза" : "Продолжить"}</Button>}
          </div>
          {message && <p className="inline-message"><Info size={15} />{message}</p>}
          {requestError && <p className="inline-error">{requestError}</p>}
        </aside>
      </div>

      {result && <SimulationMetrics result={result} />}
    </section>
  );
}

function SimulationMetrics({ result }: { result: SimulationResult }) {
  return (
    <div className="simulation-results">
      <div className="simulation-kpis">
        <article><Route /><span>Маршрут в одну сторону</span><b>{number.format(result.route_distance_m)} м</b></article>
        <article><Timer /><span>Время цикла</span><b>{number.format(result.cycle_time_seconds)} с</b></article>
        <article><Gauge /><span>Пропускная способность</span><b>{number.format(result.throughput_tasks_hour)} зад./ч</b></article>
        <article><Bot /><span>Рекомендуемый парк</span><b>{result.recommended_robots} роб.</b></article>
      </div>
      <div className="simulation-summary">
        <div>
          <span>Выполнение суточного потока</span>
          <b>{number.format(result.completed_tasks_day)} заданий/сутки</b>
          <div className="capacity-bar"><i style={{ width: `${Math.min(100, result.utilization_percent)}%` }} /></div>
          <small>Загрузка парка {number.format(result.utilization_percent)}% · доступная мощность {number.format(result.capacity_tasks_hour)} заданий/ч</small>
        </div>
        <div className="assumption-list">
          <b>Проверяемые допущения</b>
          {result.assumptions.map((item) => <p key={item.key}><Badge tone="assumed">assumed</Badge><span>{item.value} {item.unit}</span></p>)}
        </div>
      </div>
      {result.warnings.length > 0 && <div className="notice notice-warning simulation-warnings"><AlertTriangle size={18} /><div>{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div></div>}
    </div>
  );
}
