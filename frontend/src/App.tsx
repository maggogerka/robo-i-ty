import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CatalogPage } from "./pages/CatalogPage";
import { DemoPage } from "./pages/DemoPage";
import { HomePage } from "./pages/HomePage";
import { MatchingPage } from "./pages/MatchingPage";
import { PlannedPage } from "./pages/PlannedPage";
import { ProjectInputPage } from "./pages/ProjectInputPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ReportPage } from "./pages/ReportPage";

const EconomicsPage = lazy(() =>
  import("./pages/EconomicsPage").then((module) => ({ default: module.EconomicsPage })),
);

const SimulationPage = lazy(() =>
  import("./pages/SimulationPage").then((module) => ({ default: module.SimulationPage })),
);

export default function App() {
  return (
    <Suspense
      fallback={<div className="state"><span className="spinner" /><p>Загружаем модуль…</p></div>}
    >
      <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="demo" element={<DemoPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id/input" element={<ProjectInputPage />} />
        <Route path="projects/:id/matching" element={<MatchingPage />} />
        <Route path="projects/:id/economics" element={<EconomicsPage />} />
        <Route path="projects/:id/simulation" element={<SimulationPage />} />
        <Route path="projects/:id/report" element={<ReportPage />} />
        <Route path="admin" element={<PlannedPage kind="admin" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
      </Routes>
    </Suspense>
  );
}

