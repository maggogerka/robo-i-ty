import { BarChart3, Boxes, CircleUserRound, Factory, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearToken, getToken } from "../lib/api";
import { Button } from "./ui";

const nav = [
  ["/catalog", "Каталог", Boxes],
  ["/projects", "Проекты", Factory],
  ["/demo", "Демо-расчёт", BarChart3],
] as const;

export function Layout() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const logout = () => {
    clearToken();
    navigate("/");
  };
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="Робо и Ты — на главную">
          <span className="brand-mark">Р&Т</span>
          <span>Робо&Ты</span>
        </Link>
        <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="Меню">
          {open ? <X /> : <Menu />}
        </button>
        <nav className={open ? "nav nav-open" : "nav"}>
          {nav.map(([path, label, Icon]) => (
            <NavLink key={path} to={path} onClick={() => setOpen(false)}>
              <Icon size={17} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="account">
          <CircleUserRound size={18} />
          {getToken() ? (
            <Button className="button-quiet" onClick={logout}>Выйти</Button>
          ) : (
            <Link to="/demo">Войти</Link>
          )}
        </div>
      </header>
      <main><Outlet /></main>
      <footer>
        <span>Робо&Ты · предварительная инженерно-экономическая оценка</span>
        <span>Модель расчёта 2026.09.1</span>
      </footer>
    </div>
  );
}

