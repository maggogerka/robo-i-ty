import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CatalogPage } from "./pages/CatalogPage";
import { DemoPage } from "./pages/DemoPage";
import { EconomicsPage } from "./pages/EconomicsPage";
import { HomePage } from "./pages/HomePage";
import { MatchingPage } from "./pages/MatchingPage";
import { PlannedPage } from "./pages/PlannedPage";
import { ProjectInputPage } from "./pages/ProjectInputPage";
import { ProjectsPage } from "./pages/ProjectsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="demo" element={<DemoPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id/input" element={<ProjectInputPage />} />
        <Route path="projects/:id/matching" element={<MatchingPage />} />
        <Route path="projects/:id/economics" element={<EconomicsPage />} />
        <Route path="projects/:id/simulation" element={<PlannedPage kind="simulation" />} />
        <Route path="projects/:id/report" element={<PlannedPage kind="report" />} />
        <Route path="admin" element={<PlannedPage kind="admin" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

