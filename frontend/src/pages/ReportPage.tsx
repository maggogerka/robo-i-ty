import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, FileText, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { ProjectSteps } from "../components/ProjectSteps";
import { Badge, Button, ErrorState, Loading } from "../components/ui";
import { api, apiDownload } from "../lib/api";
import type { Project } from "../types";

export function ReportPage() {
  const { id = "" } = useParams();
  const [downloading, setDownloading] = useState<"pdf" | "csv" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const project = useQuery({
    queryKey: ["project", id],
    queryFn: () => api<Project>(`/projects/${id}`),
  });

  const download = async (format: "pdf" | "csv") => {
    setDownloading(format);
    setDownloadError(null);
    try {
      const path = format === "pdf"
        ? `/projects/${id}/reports/summary.pdf`
        : `/projects/${id}/exports/analysis.csv`;
      const result = await apiDownload(path);
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Не удалось сформировать файл");
    } finally {
      setDownloading(null);
    }
  };

  if (project.isPending) return <Loading label="Проверяем готовность отчёта" />;
  if (project.error || !project.data) return <ErrorState message={project.error?.message ?? "Проект не найден"} />;

  const sourceCount = project.data.parameters.filter((item) => item.source_status !== "assumed").length;
  const assumptionCount = project.data.parameters.length - sourceCount;

  return (
    <section className="page page-wide project-page report-page">
      <ProjectSteps projectId={id} />
      <div className="page-header">
        <div><p className="section-kicker">Фиксируем результат</p><h1>Отчёт и выгрузки</h1><p>Файлы формируются на сервере из текущих параметров и свежего пересчёта моделей.</p></div>
        <div className="quality-box"><span>Параметры проекта</span><b>{project.data.parameters.length} полей</b><small>{sourceCount} из источников · {assumptionCount} допущений</small></div>
      </div>

      <div className="report-grid">
        <article className="report-card report-card-primary">
          <div className="report-icon"><FileText /></div>
          <Badge tone="success">Для согласования</Badge>
          <h2>Инженерный отчёт PDF</h2>
          <p>Подбор, сценарии экономики, последняя симуляция, входные параметры, источники и ограничения методики.</p>
          <ul><li><CheckCircle2 /> Кириллица и печать A4</li><li><CheckCircle2 /> Неизвестные данные отмечены</li><li><ShieldCheck /> Без внешних ресурсов и скриптов</li></ul>
          <Button className="button-primary" disabled={downloading !== null} onClick={() => download("pdf")}><Download size={17} />{downloading === "pdf" ? "Формируем…" : "Скачать PDF"}</Button>
        </article>
        <article className="report-card">
          <div className="report-icon"><FileSpreadsheet /></div>
          <Badge tone="source">Для проверки</Badge>
          <h2>Расчётные данные CSV</h2>
          <p>Единая таблица параметров, рейтинга, экономики и симуляции с единицами, статусами и версиями моделей.</p>
          <ul><li><CheckCircle2 /> UTF-8 BOM и разделитель «;»</li><li><CheckCircle2 /> Открывается в Excel</li><li><ShieldCheck /> Защита от CSV formula injection</li></ul>
          <Button className="button-secondary" disabled={downloading !== null} onClick={() => download("csv")}><Download size={17} />{downloading === "csv" ? "Формируем…" : "Скачать CSV"}</Button>
        </article>
      </div>

      {downloadError && <div className="notice notice-warning"><AlertTriangle size={18} /><span>{downloadError}</span></div>}
      <div className="report-note"><ShieldCheck /><div><b>Контроль перед использованием</b><p>Отчёт не заменяет обследование объекта и коммерческое предложение. Проверьте строки со статусом <code>assumed</code>, запустите симуляцию после последнего изменения плана и подтвердите ТТХ у производителя.</p></div></div>
    </section>
  );
}
