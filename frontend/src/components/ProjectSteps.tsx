import { NavLink } from "react-router-dom";

const steps = [
  ["input", "01", "Параметры"],
  ["plan", "02", "План объекта"],
  ["matching", "03", "Подбор"],
  ["economics", "04", "Экономика"],
  ["simulation", "05", "2D-симуляция"],
  ["report", "06", "Отчёт"],
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

