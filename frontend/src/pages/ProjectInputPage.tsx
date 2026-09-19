import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Info, Save } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Project } from "../types";
import { ProjectSteps } from "../components/ProjectSteps";
import { Badge, Button, ErrorState, Loading } from "../components/ui";

export function ProjectInputPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const project = useQuery({ queryKey: ["project", id], queryFn: () => api<Project>(`/projects/${id}`) });
  const [draft, setDraft] = useState<Record<string, string | number>>({});
  const groups = (() => {
    const map = new Map<string, NonNullable<typeof project.data>["parameters"]>();
    project.data?.parameters.forEach((parameter) => {
      const list = map.get(parameter.section) ?? [];
      list.push(parameter);
      map.set(parameter.section, list);
    });
    return [...map.entries()];
  })();
  const save = useMutation({
    mutationFn: () => api<Project>(`/projects/${id}/parameters`, {
      method: "PATCH",
      body: JSON.stringify({ values: draft }),
    }),
    onSuccess: (data) => {
      client.setQueryData(["project", id], data);
      setDraft({});
    },
  });
  if (project.isLoading) return <Loading label="Загружаем параметры" />;
  if (project.error || !project.data) return <ErrorState message={project.error?.message ?? "Проект не найден"} />;
  return (
    <section className="page page-wide project-page">
      <ProjectSteps projectId={id} />
      <div className="page-header project-heading">
        <div><p className="section-kicker">Демопроект · склад</p><h1>{project.data.name}</h1><p>Версия расчёта {project.data.calculation_version}</p></div>
        <div className="quality-box"><span>Качество входных данных</span><b>Источник присутствует</b><small>138 полей импортированы из XLSX</small></div>
      </div>
      <div className="notice"><Info size={18} /><span><b>Демонстрационные значения.</b> Они предоставлены организатором, но не являются результатом обследования вашего объекта.</span></div>
      <div className="form-sections">
        {groups.map(([section, parameters], groupIndex) => (
          <details key={section} open={groupIndex < 3} className="form-section">
            <summary><span>{section}</span><small>{parameters.length} параметров</small><ChevronRight /></summary>
            <div className="field-grid">
              {parameters.map((parameter) => {
                const current = draft[parameter.code] ?? parameter.value ?? "";
                return (
                  <label className="field" key={parameter.code}>
                    <span>{parameter.name}{parameter.required && <i>*</i>}</span>
                    <div className="input-wrap">
                      <input
                        type={parameter.value_type === "number" ? "number" : "text"}
                        value={current}
                        min={parameter.minimum ?? undefined}
                        max={parameter.maximum ?? undefined}
                        step="any"
                        onChange={(event) => setDraft((values) => ({
                          ...values,
                          [parameter.code]: parameter.value_type === "number" ? Number(event.target.value) : event.target.value,
                        }))}
                      />
                      {parameter.unit && <span>{parameter.unit}</span>}
                    </div>
                    <small>{parameter.minimum != null ? `${parameter.minimum}–${parameter.maximum}` : parameter.note?.slice(0, 90)}</small>
                    <Badge tone={draft[parameter.code] !== undefined ? "assumed" : "source"}>
                      {draft[parameter.code] !== undefined ? "Изменено: допущение" : "Из исходного XLSX"}
                    </Badge>
                  </label>
                );
              })}
            </div>
          </details>
        ))}
      </div>
      {save.error && <ErrorState message={save.error.message} />}
      <div className="sticky-actions">
        <span>{Object.keys(draft).length ? `Изменено полей: ${Object.keys(draft).length}` : "Все изменения сохранены"}</span>
        <Button className="button-secondary" onClick={() => save.mutate()} disabled={!Object.keys(draft).length || save.isPending}><Save size={17} /> Сохранить</Button>
        <Button className="button-primary" onClick={async () => { if (Object.keys(draft).length) await save.mutateAsync(); navigate(`/projects/${id}/matching`); }}>Выполнить подбор <ChevronRight /></Button>
      </div>
    </section>
  );
}
