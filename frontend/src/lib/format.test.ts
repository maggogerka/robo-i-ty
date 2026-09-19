import { describe, expect, it } from "vitest";
import { money, percent } from "./format";

describe("форматирование расчётов", () => {
  it("форматирует миллионы рублей", () => {
    expect(money(2_700_000)).toContain("2,7 млн ₽");
  });
  it("не подменяет отсутствующий процент нулём", () => {
    expect(percent(null)).toBe("—");
  });
});

