import { NavLink } from "react-router-dom";

const steps = [
  ["input", "01", "Параметры"],
  ["matching", "02", "Подбор"],
  ["economics", "03", "Экономика"],
  ["simulation", "04", "Симуляция"],
  ["report", "05", "Отчёт"],
] as const;

export function ProjectSteps({ projectId }: { projectId: string }) {
  return (
    <nav className="steps" aria-label="Этапы проекта">
      {steps.map(([path, number, label]) => (
        <NavLink key={path} to={`/projects/${projectId}/${path}`}>
          <span>{number}</span>{label}
        </NavLink>
      ))}
    </nav>
  );
}

