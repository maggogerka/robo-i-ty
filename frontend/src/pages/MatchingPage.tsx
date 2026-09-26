import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Check, ChevronDown, CircleHelp } from "lucide-react";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ProjectSteps } from "../components/ProjectSteps";
import { Badge, Button, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import { money, statusLabel } from "../lib/format";
import type { MatchingResult } from "../types";

const factorLabel: Record<string, string> = {
  functional: "Функциональное соответствие · 25%",
  plan_feasibility: "Проходимость по плану · 25%",
  performance: "Производительность · 20%",
  economics: "Экономика · 15%",
  maturity: "Зрелость и кейсы · 10%",
  data_quality: "Качество данных · 5%",
};

export function MatchingPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const matching = useMutation({ mutationFn: () => api<MatchingResult>(`/projects/${id}/matching`, { method: "POST", body: "{}" }) });
  useEffect(() => { matching.mutate(); /* один воспроизводимый запуск при открытии */ }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="page page-wide project-page">
      <ProjectSteps projectId={id} />
      <div className="page-header"><div><p className="section-kicker">Результат модели 2026.09.1</p><h1>Объяснимый подбор</h1><p>Сначала ограничения, затем взвешенный рейтинг 0–100.</p></div>{matching.data && <div className="result-count"><b>{matching.data.candidates.length}</b><span>применимых решений</span></div>}</div>
      {matching.isPending && <Loading label="Проверяем ограничения и считаем рейтинг" />}
      {matching.error && <ErrorState message={matching.error.message} />}
      {matching.data && (
        <>
          <div className="notice notice-warning"><AlertTriangle size={18} /><span>{matching.data.disclaimer}</span></div>
          <div className="candidate-list">
            {matching.data.candidates.slice(0, 6).map((candidate) => (
              <article className="candidate-card" key={candidate.solution_id}>
                <div className="rank">#{candidate.rank}</div>
                <div className="candidate-main">
                  <div className="candidate-title"><div><Badge tone={candidate.status === "operation" ? "success" : "neutral"}>{statusLabel[candidate.status] ?? candidate.status}</Badge><h2>{candidate.name}</h2><p>{candidate.manufacturer}</p></div><div className="score"><b>{candidate.score}</b><span>из 100</span></div></div>
                  <div className="score-bars">
                    {Object.entries(candidate.contributions).map(([key, value]) => <div key={key}><span>{factorLabel[key]}</span><div><i style={{ width: `${Math.min(100, value * 4)}%` }} /></div><b>+{value}</b></div>)}
                  </div>
                  <div className="candidate-foot"><span className="price">{money(candidate.price_rub)}</span>{candidate.requires_verification && <span className="verify"><CircleHelp size={16} /> Есть неполные ТТХ</span>}</div>
                  <details className="explain"><summary>Почему это решение <ChevronDown size={17} /></summary><div className="explain-grid"><div><b>Пройдено</b>{candidate.constraints.filter((x) => x.status === "passed").map((item) => <p key={item.code}><Check size={14} /> {item.detail}</p>)}</div><div><b>Требует проверки</b>{candidate.missing_data.map((item) => <p key={item}><CircleHelp size={14} /> {item}</p>)}</div></div></details>
                </div>
                {candidate.rank === 1 && <Button className="button-primary choose" onClick={() => navigate(`/projects/${id}/economics?solution=${candidate.solution_id}`)}>Рассчитать экономику <ArrowRight size={17} /></Button>}
              </article>
            ))}
          </div>
          <details className="excluded"><summary>Исключённые решения ({matching.data.excluded.length} показано)</summary>{matching.data.excluded.slice(0, 8).map((item) => <div key={item.solution_id}><span>{item.name}</span><small>{item.constraints.find((x) => x.status === "failed")?.detail}</small></div>)}</details>
        </>
      )}
    </section>
  );
}

