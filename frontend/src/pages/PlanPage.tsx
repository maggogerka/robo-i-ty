import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Ban,
  Box,
  DoorOpen,
  History,
  MapPin,
  Redo2,
  Save,
  ScanLine,
  ShieldAlert,
  SquareDashed,
  Trash2,
  Undo2,
  Upload,
  BrickWall,
  Zap,
} from "lucide-react";
import { useParams } from "react-router-dom";
import {
  PlanEditorCanvas,
  type CalibrationPoint,
} from "../components/PlanEditorCanvas";
import { ProjectSteps } from "../components/ProjectSteps";
import { Badge, Button, ErrorState, Loading } from "../components/ui";
import { api, apiDownload, apiUpload } from "../lib/api";
import {
  createHistory,
  pushHistory,
  redoHistory,
  undoHistory,
  type PlanHistory,
} from "../lib/planHistory";
import type {
  PlanAsset,
  PlanElement,
  PlanElementKind,
  PlanRevision,
  ProjectPlan,
  RecognitionProvider,
  RecognitionResult,
} from "../types";

const labels: Record<PlanElementKind, string> = {
  wall: "Стена",
  door: "Дверь",
  storage: "Стеллаж",
  obstacle: "Препятствие",
  work_zone: "Рабочая зона",
  restricted_zone: "Запретная зона",
  pickup: "Точка забора",
  dropoff: "Точка доставки",
  charger: "Зарядная станция",
};

const addButtons: { kind: PlanElementKind; icon: typeof Box }[] = [
  { kind: "wall", icon: BrickWall },
  { kind: "door", icon: DoorOpen },
  { kind: "storage", icon: Box },
  { kind: "obstacle", icon: Ban },
  { kind: "work_zone", icon: SquareDashed },
  { kind: "restricted_zone", icon: ShieldAlert },
  { kind: "pickup", icon: MapPin },
  { kind: "dropoff", icon: MapPin },
  { kind: "charger", icon: Zap },
];

function normalizeElement(element: Partial<PlanElement> & Pick<PlanElement, "id" | "kind">): PlanElement {
  return {
    label: labels[element.kind],
    x_m: 0,
    y_m: 0,
    width_m: 1,
    height_m: 1,
    rotation_deg: 0,
    confidence: 1,
    source: "manual",
    review_status: "reviewed",
    source_region: null,
    ...element,
  };
}

function normalizePlan(plan: Partial<ProjectPlan> & Pick<ProjectPlan, "elements">): ProjectPlan {
  return {
    name: "План объекта",
    width_m: 60,
    height_m: 36,
    revision: 0,
    source_status: "assumed",
    asset_id: null,
    scale_m_per_px: null,
    scale_status: "confirmed",
    review_status: "draft",
    provider_key: "manual",
    ...plan,
    elements: plan.elements.map(normalizeElement),
  };
}

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

export function PlanPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [history, setHistory] = useState<PlanHistory<ProjectPlan> | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeAssetId, setActiveAssetId] = useState<string | null>(null);
  const [backgroundUrl, setBackgroundUrl] = useState<string | null>(null);
  const [backgroundSize, setBackgroundSize] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const [calibrationMode, setCalibrationMode] = useState(false);
  const [calibrationPoints, setCalibrationPoints] = useState<CalibrationPoint[]>([]);
  const [knownDistance, setKnownDistance] = useState(10);
  const [message, setMessage] = useState<string | null>(null);

  const planQuery = useQuery({
    queryKey: ["plan", id],
    queryFn: () => api<ProjectPlan>(`/projects/${id}/plan`),
    enabled: Boolean(id),
  });
  const assetsQuery = useQuery({
    queryKey: ["plan-assets", id],
    queryFn: () => api<PlanAsset[]>(`/projects/${id}/plan-assets`),
    enabled: Boolean(id),
  });
  const providersQuery = useQuery({
    queryKey: ["recognition-providers", id],
    queryFn: () =>
      api<RecognitionProvider[]>(`/projects/${id}/plan-recognition/providers`),
    enabled: Boolean(id),
  });
  const revisionsQuery = useQuery({
    queryKey: ["plan-revisions", id],
    queryFn: () => api<PlanRevision[]>(`/projects/${id}/plan-revisions`),
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (!planQuery.data) return;
    const next = normalizePlan(planQuery.data);
    setHistory(createHistory(next));
    setActiveAssetId(next.asset_id);
  }, [planQuery.data]);

  const activeAsset = useMemo(
    () =>
      assetsQuery.data?.find((asset) => asset.id === activeAssetId) ??
      assetsQuery.data?.[0] ??
      null,
    [activeAssetId, assetsQuery.data],
  );

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setBackgroundUrl(null);
    if (!activeAsset?.media_type.startsWith("image/")) return;
    apiDownload(activeAsset.content_url)
      .then(({ blob }) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBackgroundUrl(objectUrl);
      })
      .catch(() => setMessage("Не удалось загрузить фон чертежа"));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [activeAsset]);

  const plan = history?.present ?? null;
  const selected = plan?.elements.find((item) => item.id === selectedId) ?? null;

  const commit = (next: ProjectPlan) => {
    setHistory((current) => (current ? pushHistory(current, next) : createHistory(next)));
    setMessage(null);
  };

  const updateElement = (elementId: string, changes: Partial<PlanElement>) => {
    if (!plan) return;
    commit({
      ...plan,
      review_status: "draft",
      elements: plan.elements.map((item) =>
        item.id === elementId
          ? {
              ...item,
              ...changes,
              source: changes.source ?? "manual",
              review_status: changes.review_status ?? "reviewed",
            }
          : item,
      ),
    });
  };

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      apiUpload<PlanAsset>(`/projects/${id}/plan-assets`, file),
    onSuccess: (asset) => {
      setActiveAssetId(asset.id);
      setMessage(`Файл «${asset.original_name}» безопасно загружен`);
      queryClient.invalidateQueries({ queryKey: ["plan-assets", id] });
    },
  });

  const recognitionMutation = useMutation({
    mutationFn: ({ assetId, provider }: { assetId: string; provider: string }) =>
      api<RecognitionResult>(
        `/projects/${id}/plan-assets/${assetId}/recognize?provider=${encodeURIComponent(provider)}`,
        { method: "POST" },
      ),
    onSuccess: (result) => {
      const draft = normalizePlan({
        ...result.plan,
        revision: 0,
        source_status: "assumed",
      });
      setHistory(createHistory(draft));
      setSelectedId(null);
      setMessage(
        result.provider.uses_model
          ? `Черновик распознан через ${result.provider.display_name}`
          : "Применён демонстрационный шаблон — это не нейросеть",
      );
      queryClient.invalidateQueries({ queryKey: ["plan-revisions", id] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: (current: ProjectPlan) =>
      api<ProjectPlan>(`/projects/${id}/plan`, {
        method: "PUT",
        body: JSON.stringify(planForApi(current)),
      }),
    onSuccess: (saved) => {
      const next = normalizePlan(saved);
      setHistory(createHistory(next));
      setMessage(`План сохранён · версия ревизии ${saved.revision}`);
      queryClient.setQueryData(["plan", id], next);
      queryClient.invalidateQueries({ queryKey: ["plan-revisions", id] });
    },
  });

  const addElement = (kind: PlanElementKind) => {
    if (!plan || plan.elements.length >= 250) return;
    const ordinal = plan.elements.filter((item) => item.kind === kind).length + 1;
    const thin = kind === "wall" || kind === "door";
    const element = normalizeElement({
      id: `${kind}-${Date.now().toString(36)}`,
      kind,
      label: `${labels[kind]} ${ordinal}`,
      x_m: Math.min(plan.width_m - 2, 2 + (ordinal % 6) * 2),
      y_m: Math.min(plan.height_m - 2, 2 + (ordinal % 5) * 2),
      width_m: thin ? 8 : 6,
      height_m: thin ? 0.4 : 6,
    });
    commit({ ...plan, elements: [...plan.elements, element] });
    setSelectedId(element.id);
  };

  const removeSelected = () => {
    if (!plan || !selected) return;
    commit({
      ...plan,
      elements: plan.elements.filter((item) => item.id !== selected.id),
    });
    setSelectedId(null);
  };

  const applyCalibration = () => {
    if (!plan || !backgroundSize || calibrationPoints.length !== 2) {
      setMessage("Укажите две точки на изображении и задайте известное расстояние");
      return;
    }
    const [first, second] = calibrationPoints;
    const pixelDistance = Math.hypot(
      second.x_px - first.x_px,
      second.y_px - first.y_px,
    );
    if (pixelDistance <= 0 || knownDistance <= 0) return;
    const metersPerPixel = knownDistance / pixelDistance;
    const width = backgroundSize.width * metersPerPixel;
    const height = backgroundSize.height * metersPerPixel;
    const factorX = width / plan.width_m;
    const factorY = height / plan.height_m;
    commit({
      ...plan,
      width_m: width,
      height_m: height,
      scale_m_per_px: metersPerPixel,
      scale_status: "confirmed",
      elements: plan.elements.map((item) => ({
        ...item,
        x_m: item.x_m * factorX,
        y_m: item.y_m * factorY,
        width_m: item.width_m * factorX,
        height_m: item.height_m * factorY,
      })),
    });
    setCalibrationMode(false);
    setCalibrationPoints([]);
    setMessage(`Масштаб подтверждён: ${metersPerPixel.toFixed(5)} м/пикс.`);
  };

  const confirmPlan = () => {
    if (!plan) return;
    const errors: string[] = [];
    if (plan.asset_id && plan.scale_status !== "confirmed") {
      errors.push("не подтверждён масштаб");
    }
    if (!plan.elements.some((item) => item.kind === "pickup")) {
      errors.push("нет точки забора");
    }
    if (!plan.elements.some((item) => item.kind === "dropoff")) {
      errors.push("нет точки доставки");
    }
    if (errors.length) {
      setMessage(`План нельзя подтвердить: ${errors.join(", ")}`);
      return;
    }
    commit({
      ...plan,
      review_status: "confirmed",
      elements: plan.elements.map((item) => ({
        ...item,
        review_status: "confirmed",
      })),
    });
    setMessage("План готов к сохранению версии и симуляции");
  };

  if (planQuery.isPending || !plan) return <Loading label="Загружаем план объекта" />;
  if (planQuery.error) return <ErrorState message={planQuery.error.message} />;

  const error =
    uploadMutation.error?.message ??
    recognitionMutation.error?.message ??
    saveMutation.error?.message;

  return (
    <section className="page page-wide project-page plan-page">
      <ProjectSteps projectId={id} />
      <div className="page-header">
        <div>
          <p className="section-kicker">Безопасная загрузка · ревизии · ручная проверка</p>
          <h1>План объекта</h1>
          <p>
            Загрузите чертёж или создайте план вручную, подтвердите масштаб и проверьте
            каждый найденный объект.
          </p>
        </div>
        <div className="quality-box">
          <span>Статус проверки</span>
          <b>{plan.review_status}</b>
          <small>
            {plan.elements.length} элементов · провайдер {plan.provider_key}
          </small>
        </div>
      </div>

      <div className="plan-source-panel">
        <label className="upload-control">
          <Upload size={18} />
          <span>{uploadMutation.isPending ? "Загружаем файл" : "Загрузить чертёж"}</span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.svg"
            disabled={uploadMutation.isPending}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadMutation.mutate(file);
              event.currentTarget.value = "";
            }}
          />
        </label>
        {activeAsset && (
          <div className="asset-summary">
            <b>{activeAsset.original_name}</b>
            <small>
              {activeAsset.media_type} · {(activeAsset.byte_size / 1024).toFixed(1)} КБ ·
              SHA-256 {activeAsset.sha256.slice(0, 12)}…
            </small>
          </div>
        )}
        <div className="provider-actions">
          {(providersQuery.data ?? []).map((provider) => (
            <Button
              key={provider.key}
              disabled={!activeAsset || !provider.available || recognitionMutation.isPending}
              onClick={() =>
                activeAsset &&
                recognitionMutation.mutate({
                  assetId: activeAsset.id,
                  provider: provider.key,
                })
              }
            >
              <ScanLine size={16} />
              {provider.display_name}
              <Badge tone={provider.uses_model ? "source" : "assumed"}>
                {provider.uses_model ? "модель" : "демо, не ИИ"}
              </Badge>
            </Button>
          ))}
        </div>
        {activeAsset?.media_type === "application/pdf" && (
          <small className="asset-warning">
            PDF сохранён безопасно. В MVP фон для интерактивного редактирования доступен для
            PNG/JPG/WebP/SVG; PDF можно обработать подключённым провайдером.
          </small>
        )}
      </div>

      <div className="simulation-toolbar plan-toolbar" aria-label="Инструменты плана">
        {addButtons.map(({ kind, icon: Icon }) => (
          <Button key={kind} onClick={() => addElement(kind)}>
            <Icon size={15} /> {labels[kind]}
          </Button>
        ))}
        <Button
          disabled={!history?.past.length}
          onClick={() => setHistory((current) => (current ? undoHistory(current) : current))}
        >
          <Undo2 size={16} /> Назад
        </Button>
        <Button
          disabled={!history?.future.length}
          onClick={() => setHistory((current) => (current ? redoHistory(current) : current))}
        >
          <Redo2 size={16} /> Вперёд
        </Button>
        <Button className="button-danger" disabled={!selected} onClick={removeSelected}>
          <Trash2 size={16} /> Удалить
        </Button>
      </div>

      <div className="plan-editor-layout">
        <PlanEditorCanvas
          plan={plan}
          backgroundUrl={backgroundUrl}
          selectedId={selectedId}
          calibrationMode={calibrationMode}
          calibrationPoints={calibrationPoints}
          onSelect={setSelectedId}
          onChangeElement={updateElement}
          onCalibrationPoint={(point) =>
            setCalibrationPoints((current) => [...current.slice(-1), point])
          }
          onBackgroundSize={setBackgroundSize}
        />

        <aside className="simulation-panel">
          <div className="panel-section">
            <p className="section-kicker">Масштаб</p>
            <p>
              {plan.scale_status === "confirmed"
                ? `подтверждён · ${plan.scale_m_per_px?.toFixed(5) ?? "ручной план"} м/пикс.`
                : "неизвестен — требуется калибровка"}
            </p>
            <label className="compact-field">
              <span>Известное расстояние, м</span>
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={knownDistance}
                onChange={(event) => setKnownDistance(Number(event.target.value))}
              />
            </label>
            <Button
              className={calibrationMode ? "button-primary" : ""}
              disabled={!backgroundSize}
              onClick={() => {
                setCalibrationMode((value) => !value);
                setCalibrationPoints([]);
              }}
            >
              <ScanLine size={16} /> Выбрать две точки
            </Button>
            {calibrationPoints.length === 2 && (
              <Button className="button-primary" onClick={applyCalibration}>
                Применить масштаб
              </Button>
            )}
          </div>

          {selected && (
            <div className="panel-section selected-editor">
              <span>Выбран объект</span>
              <label className="compact-field">
                <span>Тип</span>
                <select
                  value={selected.kind}
                  onChange={(event) =>
                    updateElement(selected.id, {
                      kind: event.target.value as PlanElementKind,
                    })
                  }
                >
                  {(Object.keys(labels) as PlanElementKind[]).map((kind) => (
                    <option key={kind} value={kind}>
                      {labels[kind]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="compact-field">
                <span>Название</span>
                <input
                  value={selected.label}
                  onChange={(event) =>
                    updateElement(selected.id, { label: event.target.value })
                  }
                />
              </label>
              <div className="coordinate-grid">
                {(["x_m", "y_m", "width_m", "height_m"] as const).map((key) => (
                  <label className="compact-field" key={key}>
                    <span>{key.replace("_m", "")}, м</span>
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={Number(selected[key].toFixed(3))}
                      onChange={(event) =>
                        updateElement(selected.id, {
                          [key]: Number(event.target.value),
                        })
                      }
                    />
                  </label>
                ))}
              </div>
              <p className={selected.confidence < 0.7 ? "inline-error" : "inline-message"}>
                confidence {(selected.confidence * 100).toFixed(0)}% ·
                {selected.source} · {selected.review_status}
              </p>
            </div>
          )}

          <div className="simulation-actions">
            <Button onClick={confirmPlan}>Подтвердить план</Button>
            <Button
              className="button-primary"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate(plan)}
            >
              <Save size={17} /> Сохранить версию
            </Button>
          </div>
          {message && <p className="inline-message">{message}</p>}
          {error && <p className="inline-error">{error}</p>}
        </aside>
      </div>

      <details className="revision-history">
        <summary>
          <History size={17} /> История версий ({revisionsQuery.data?.length ?? 0})
        </summary>
        {(revisionsQuery.data ?? []).map((revision) => (
          <div key={revision.id}>
            <span>
              №{revision.revision_number} · {revision.source} · {revision.provider_key}
            </span>
            <Button
              onClick={() => {
                setHistory(createHistory(normalizePlan(revision.plan)));
                setActiveAssetId(revision.asset_id);
                setMessage(`Открыта версия №${revision.revision_number}; сохраните её для новой ревизии`);
              }}
            >
              Открыть
            </Button>
          </div>
        ))}
      </details>
    </section>
  );
}

