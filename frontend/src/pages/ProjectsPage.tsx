import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FolderKanban } from "lucide-react";
import { Link } from "react-router-dom";
import { api, getToken } from "../lib/api";
import { EmptyState, ErrorState, Loading } from "../components/ui";

type ProjectSummary = { id: string; name: string; object_type_code: string; is_demo: boolean };

export function ProjectsPage() {
  const query = useQuery({
    queryKey: ["projects"],
    queryFn: () => api<ProjectSummary[]>("/projects"),
    enabled: Boolean(getToken()),
  });
  if (!getToken()) return <EmptyState><p>Сначала откройте демо-проект.</p><Link className="button button-primary" to="/demo">Перейти к демо</Link></EmptyState>;
  if (query.isLoading) return <Loading />;
  if (query.error) return <ErrorState message={query.error.message} />;
  return (
    <section className="page page-wide">
      <div className="page-header"><div><p className="section-kicker">Рабочая область</p><h1>Проекты</h1></div></div>
      <div className="project-list">
        {query.data?.map((project) => (
          <Link to={`/projects/${project.id}/input`} className="project-row" key={project.id}>
            <FolderKanban /><div><b>{project.name}</b><span>{project.object_type_code === "warehouse" ? "Склад" : project.object_type_code}</span></div>
            {project.is_demo && <span className="badge badge-source">Демо</span>}<ArrowRight />
          </Link>
        ))}
      </div>
    </section>
  );
}

