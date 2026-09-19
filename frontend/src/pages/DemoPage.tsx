import { useMutation } from "@tanstack/react-query";
import { ArrowRight, KeyRound, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../lib/api";
import type { Project } from "../types";
import { Button, Card, ErrorState } from "../components/ui";

type LoginResponse = { access_token: string };

export function DemoPage() {
  const navigate = useNavigate();
  const launch = useMutation({
    mutationFn: async () => {
      const login = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "demo@robo.local", password: "Demo-2026!" }),
      });
      setToken(login.access_token);
      return api<Project>("/projects/demo", { method: "POST", body: "{}" });
    },
    onSuccess: (project) => navigate(`/projects/${project.id}/input`),
  });

  return (
    <section className="demo-gate page-narrow">
      <div className="eyebrow"><span /> Воспроизводимый сценарий</div>
      <h1>Распределительный склад<br />за один клик</h1>
      <p className="lead">
        Откроем сохранённый набор параметров, выполним подбор по фиксированной модели и
        рассчитаем три варианта владения.
      </p>
      <Card className="demo-card">
        <div className="demo-icon"><KeyRound /></div>
        <div>
          <span className="overline">Демо-пользователь</span>
          <b>demo@robo.local</b>
          <small>Доступ только к собственному демопроекту</small>
        </div>
        <ShieldCheck className="shield" />
      </Card>
      {launch.error && <ErrorState message={launch.error.message} />}
      <Button className="button-primary button-large" onClick={() => launch.mutate()} disabled={launch.isPending}>
        {launch.isPending ? "Готовим проект…" : "Запустить демо"} <ArrowRight size={19} />
      </Button>
      <p className="fine-print">Значения помечены статусом источника. Изменения пользователя сохраняются как допущения.</p>
    </section>
  );
}

