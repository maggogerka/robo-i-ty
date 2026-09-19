import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, Bot, Calculator, Info } from "lucide-react";
import { useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { ProjectSteps } from "../components/ProjectSteps";
import { SensitivityChart } from "../components/SensitivityChart";
import { Badge, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import { money, percent } from "../lib/format";
import type { EconomicsResult } from "../types";

export function EconomicsPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const solutionId = params.get("solution");
  const economics = useMutation({
    mutationFn: () => api<EconomicsResult>(`/projects/${id}/economics`, {
      method: "POST",
      body: JSON.stringify({ solution_id: solutionId }),
    }),
  });
  useEffect(() => { economics.mutate(); /* расчёт при открытии */ }, [id, solutionId]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="page page-wide project-page">
      <ProjectSteps projectId={id} />
      <div className="page-header"><div><p className="section-kicker">Предварительный ТЭО</p><h1>Экономика сценариев</h1><p>Единицы, формулы и допущения доступны для проверки.</p></div></div>
      {economics.isPending && <Loading label="Рассчитываем CAPEX, OPEX, ROI и TCO" />}
      {economics.error && <ErrorState message={economics.error.message} />}
      {economics.data && <EconomicsView result={economics.data} />}
    </section>
  );
}

function EconomicsView({ result }: { result: EconomicsResult }) {
  const order = ["baseline", "purchase", "raas"] as const;
  return (
    <>
      <div className="solution-strip"><Bot /><div><small>Решение для расчёта</small><b>{result.solution.name}</b><span>{result.solution.manufacturer} · {money(result.solution.price_rub)} за единицу</span></div><div className="fleet"><b>{result.required_robots}</b><span>роботов в парке</span></div></div>
      <div className="scenario-grid">
        {order.map((key) => {
          const item = result.scenarios[key];
          return (
            <article key={key} className={`scenario-card ${key === "purchase" ? "scenario-featured" : ""}`}>
              <div className="scenario-head"><span>{key === "baseline" ? "00" : key === "purchase" ? "01" : "02"}</span><h2>{item.name}</h2>{key === "purchase" && <Badge tone="success">Рекомендуемый</Badge>}</div>
              <dl><div><dt>CAPEX</dt><dd>{money(item.capex_rub)}</dd></div><div><dt>OPEX в год</dt><dd>{money(item.annual_opex_rub)}</dd></div><div><dt>Эффект в год</dt><dd className={item.annual_effect_rub > 0 ? "positive" : "negative"}>{money(item.annual_effect_rub)}</dd></div><div><dt>TCO за {result.horizon_years} лет</dt><dd>{money(item.tco_rub)}</dd></div></dl>
              <div className="scenario-kpis"><div><span>Окупаемость</span><b>{item.payback_years == null ? "Не окупается" : `${item.payback_years} года`}</b></div><div><span>ROI горизонта</span><b>{percent(item.roi_horizon_percent)}</b></div></div>
            </article>
          );
        })}
      </div>
      <div className="economics-lower">
        <article className="chart-card"><div><p className="section-kicker">What-if · ±20%</p><h2>Чувствительность окупаемости</h2></div><SensitivityChart data={result.sensitivity} /></article>
        <aside className="method-card"><Calculator /><h3>Методика</h3><p>{result.formula_note}</p><div><Info size={16} /><span>Требуемое число роботов округляется вверх с учётом пика и загрузки.</span></div><div><AlertTriangle size={16} /><span>{result.disclaimer}</span></div></aside>
      </div>
    </>
  );
}

