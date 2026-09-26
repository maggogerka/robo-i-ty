"""Формирует безопасный агрегированный аудит каталога без вывода строк источника."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "input" / "catalog_export_v4.csv"
REPORT = ROOT / "docs" / "catalog-audit-2026-09-26.md"
CONFIGURATION_FIELDS = (
    "Название",
    "тип",
    "статус",
    "компания",
    "Тип",
    "Подтип",
    "Цена изделия",
)


def main() -> None:
    raw = SOURCE.read_bytes()
    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        headers = reader.fieldnames or []
        rows = list(reader)

    ids = Counter((row.get("id") or "").strip() for row in rows)
    duplicate_ids = {key for key, count in ids.items() if key and count > 1}
    signatures: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for row in rows:
        signatures[(row.get("id") or "").strip()].add(
            tuple((row.get(field) or "").strip() for field in CONFIGURATION_FIELDS)
        )
    conflict_groups = sum(len(items) > 1 for items in signatures.values())
    configuration_count = sum(len(items) for items in signatures.values())
    case_insensitive_duplicates = len(headers) - len(
        {header.casefold() for header in headers}
    )

    fill_rows = []
    for header in headers:
        filled = sum(bool((row.get(header) or "").strip()) for row in rows)
        fill_rows.append(f"| `{header}` | {filled} | {filled / len(rows) * 100:.1f}% |")

    report = f"""# Аудит каталога от 2026-09-26

Аудит содержит только структуру и агрегаты. Строки, названия решений и пользовательские файлы не публикуются.

- Файл: `input/catalog_export_v4.csv` (не коммитится).
- Размер: {len(raw)} байт.
- SHA-256: `{hashlib.sha256(raw).hexdigest()}`.
- Строк: {len(rows)}; колонок: {len(headers)}.
- Уникальных исходных ID: {len(signatures)}.
- Групп с повторяющимся ID: {len(duplicate_ids)}.
- Групп, где один ID описывает разные конфигурации: {conflict_groups}.
- Конфигураций после нормализации: {configuration_count}.
- Коллизий заголовков без учёта регистра: {case_insensitive_duplicates}. Поэтому импорт использует точные регистрозависимые имена колонок.

## Заполненность

| Колонка | Заполнено | Доля |
|---|---:|---:|
{chr(10).join(fill_rows)}

## Решение по импорту

`id` источника становится идентификатором семейства, а отличающиеся базовые атрибуты — отдельными конфигурациями. Повторные строки одной конфигурации не затирают друг друга: номера строк сохраняются в `attributes.source_rows`, кейсы остаются отдельными записями. Отсутствующие ТТХ остаются `null`; ширина, длина и радиус разворота не выводятся из маркетингового текста.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(
        {
            "rows": len(rows),
            "columns": len(headers),
            "families": len(signatures),
            "configurations": configuration_count,
            "conflict_groups": conflict_groups,
        }
    )


if __name__ == "__main__":
    main()
