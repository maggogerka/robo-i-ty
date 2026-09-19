export function money(value: number | null | undefined): string {
  if (value == null) return "нет данных";
  if (Math.abs(value) >= 1_000_000) {
    return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value / 1_000_000)} млн ₽`;
  }
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)} ₽`;
}

export function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value)}%`;
}

export const statusLabel: Record<string, string> = {
  operation: "Эксплуатация",
  piloting: "Пилотирование",
  rnd: "Разработка",
  source_present: "Есть в источнике",
  assumed: "Допущение",
  verified: "Проверено",
};

