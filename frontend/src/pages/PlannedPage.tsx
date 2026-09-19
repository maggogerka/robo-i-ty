import { Construction, ExternalLink } from "lucide-react";
import { useParams } from "react-router-dom";
import { ProjectSteps } from "../components/ProjectSteps";

export function PlannedPage({ kind }: { kind: "simulation" | "report" | "admin" }) {
  const { id = "" } = useParams();
  const content = {
    simulation: ["2D-симуляция", "Следующий P0-инкремент: детерминированное ядро, движение по маршрутам и проверка пропускной способности."],
    report: ["Отчёт и экспорт", "Следующий P0-инкремент: PDF с методикой и CSV с входами, рейтингом и экономикой."],
    admin: ["Управление каталогом", "API проверки роли и редактирования уже работает; визуальный CRUD будет добавлен следующим этапом."],
  }[kind];
  return <section className="page page-wide project-page">{id && <ProjectSteps projectId={id} />}<div className="planned"><Construction /><p className="section-kicker">Статус: следующий инкремент</p><h1>{content[0]}</h1><p>{content[1]}</p><a href="/docs" onClick={(event) => event.preventDefault()}>См. план развития <ExternalLink size={16} /></a></div></section>;
}

