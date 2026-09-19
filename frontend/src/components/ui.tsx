import type { ButtonHTMLAttributes, HTMLAttributes, PropsWithChildren } from "react";

export function Button({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`button ${className}`} {...props} />;
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${className}`} {...props} />;
}

export function Badge({ tone = "neutral", children }: PropsWithChildren<{ tone?: string }>) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Loading({ label = "Загружаем данные" }: { label?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" />
      <p>{label}…</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state state-error" role="alert">
      <strong>Не удалось выполнить запрос</strong>
      <p>{message}</p>
    </div>
  );
}

export function EmptyState({ children }: PropsWithChildren) {
  return <div className="state">{children}</div>;
}

