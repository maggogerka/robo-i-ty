"""Создаёт воспроизводимые JSON-seed из файлов организатора в input/.

Скрипт не пытается обогащать отсутствующие ТТХ. Значения, которых нет в
источниках, остаются ``null``. Запуск из корня репозитория:

    python scripts/build_seed.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input"
OUTPUT = ROOT / "data" / "seed"

OBJECT_CODES = {
    "Склад": ("warehouse", "Склад", "Полная демонстрационная модель"),
    "Аэропорт": ("airport", "Аэропорт", "Базовая модель"),
    "Медучреждение": ("healthcare", "Медицинское учреждение", "Базовая модель"),
}

KNOWN_CODES = {
    "Общая площадь склада": "total_area_m2",
    "Площадь активной (роботизируемой) зоны": "active_area_m2",
    "Ширина главных проездов": "main_aisle_width_m",
    "Ширина рабочих проходов между стеллажами": "working_aisle_width_m",
    "Тип напольного покрытия": "floor_type",
    "Количество рабочих смен в сутки": "shifts_per_day",
    "Рабочих дней в году": "working_days_per_year",
    "Продолжительность смены": "shift_hours",
    "Пиковый коэффициент нагрузки": "peak_factor",
    "Объём отбора (строк/сутки, всего)": "daily_tasks",
    "Общая численность персонала склада": "total_staff",
    "Из них: отборщики (комплектовщики)": "target_staff",
    "Средняя з/п отборщика (gross)": "monthly_labor_cost_rub",
    "Коэффициент начислений на ФОТ (страховые взносы)": "payroll_factor",
    "Средняя длина маршрута отборщика на 1 строку": "route_length_m",
    "Средняя масса грузовой единицы (паллет)": "payload_kg",
    "Мощность электроснабжения (доступная)": "power_kw",
    "Наличие WMS": "has_wms",
    "Планируемый бюджет на роботизацию (CAPEX)": "budget_mln_rub",
    "Горизонт расчёта окупаемости": "horizon_years",
    "Среднесуточное количество пассажиров": "daily_tasks",
    "Численность персонала внутри терминала (логистика, уборка)": "target_staff",
    "Средняя з/п сотрудника наземного обслуживания (gross)": "monthly_labor_cost_rub",
    "Коэффициент начислений на ФОТ": "payroll_factor",
    "Общая площадь здания(й)": "total_area_m2",
    "Объём выдачи медикаментов (заявок/сутки)": "daily_tasks",
    "Численность санитаров и транспортировщиков": "target_staff",
    "Средняя з/п санитара/транспортировщика (gross)": "monthly_labor_cost_rub",
    "Ширина коридоров (основных)": "working_aisle_width_m",
}


def slug(value: str) -> str:
    translit = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "abvgdeejzijklmnoprstufhccss_y_eua",
    )
    value = unicodedata.normalize("NFKD", value.lower()).translate(translit)
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")[:64]


def clean_bound(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def build_object_types(path: Path) -> list[dict[str, Any]]:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    result: list[dict[str, Any]] = []
    for sheet_name, (code, label, readiness) in OBJECT_CODES.items():
        sheet = workbook[sheet_name]
        parameters: list[dict[str, Any]] = []
        section = "Общие параметры"
        used_codes: set[str] = set()
        for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            name, unit, baseline, minimum, maximum, note = (list(row) + [None] * 6)[:6]
            if not name:
                continue
            name = str(name).strip()
            if name.startswith("▌"):
                section = name.replace("▌", "").strip().title()
                continue
            if name.startswith("ДЕМО-") or name == "Параметр":
                continue
            parameter_code = KNOWN_CODES.get(name) or f"{code}_{slug(name)}"
            if parameter_code in used_codes:
                parameter_code = f"{parameter_code}_{row_number}"
            used_codes.add(parameter_code)
            parameters.append(
                {
                    "code": parameter_code,
                    "name": name,
                    "section": section,
                    "unit": None if unit in (None, "-") else str(unit),
                    "baseline": baseline,
                    "minimum": clean_bound(minimum),
                    "maximum": clean_bound(maximum),
                    "required": parameter_code
                    in {
                        "daily_tasks",
                        "target_staff",
                        "monthly_labor_cost_rub",
                        "horizon_years",
                    },
                    "value_type": "number"
                    if isinstance(baseline, (int, float))
                    else "text",
                    "note": note,
                    "source_status": "source_present",
                    "source_name": "Датасеты_хакатон.xlsx",
                }
            )
        result.append(
            {
                "code": code,
                "name": label,
                "readiness": readiness,
                "parameters": parameters,
            }
        )
    return result


def parse_price(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def parse_payload(name: str) -> float | None:
    match = re.search(r"грузоподъ[её]мность\s+до\s+([\d\s]+)\s*кг", name.lower())
    return float(match.group(1).replace(" ", "")) if match else None


def build_catalog(path: Path) -> dict[str, list[dict[str, Any]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))

    configuration_fields = (
        "Название",
        "тип",
        "статус",
        "компания",
        "Тип",
        "Подтип",
        "Цена изделия",
    )

    def signature(row: dict[str, str]) -> str:
        values = {key: (row.get(key) or "").strip() for key in configuration_fields}
        encoded = json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    signatures_by_source: dict[str, list[str]] = {}
    for row in rows:
        source_id = row["id"].strip()
        item_signature = signature(row)
        signatures = signatures_by_source.setdefault(source_id, [])
        if item_signature not in signatures:
            signatures.append(item_signature)

    products: dict[str, dict[str, Any]] = {}
    families: dict[str, dict[str, Any]] = {}
    cases: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        source_id = row["id"].strip()
        item_signature = signature(row)
        configuration_index = signatures_by_source[source_id].index(item_signature) + 1
        has_variants = len(signatures_by_source[source_id]) > 1
        solution_id = (
            source_id
            if configuration_index == 1
            else f"{source_id}-cfg-{item_signature[:8]}"
        )
        family_id = (
            f"family-{hashlib.sha256(source_id.encode('utf-8')).hexdigest()[:16]}"
        )
        present = sum(bool((row.get(key) or "").strip()) for key in row)
        families.setdefault(
            family_id,
            {
                "id": family_id,
                "name": row["Название"].strip(),
                "manufacturer": row["компания"].strip(),
                "source_status": "source_present",
                "source_name": "catalog_export_v4.csv",
            },
        )
        product = products.setdefault(
            solution_id,
            {
                "id": solution_id,
                "family_id": family_id,
                "source_product_id": source_id,
                "configuration_key": item_signature,
                "name": row["Название"].strip(),
                "manufacturer": row["компания"].strip(),
                "catalog_type": row["Тип"].strip() or None,
                "subtype": row["Подтип"].strip() or None,
                "status": row["статус"].strip(),
                "description": row["описание"].strip() or None,
                "process": row["Сценарий"].strip() or None,
                "trl": int(row["УГТ"]) if row["УГТ"].strip().isdigit() else None,
                "market_potential": parse_price(row["Рын Потенциал"]),
                "region": row["Регион"].strip() or None,
                "industry": row["Отрасль"].strip() or None,
                "price_rub": parse_price(row["Цена изделия"]),
                "max_payload_kg": parse_payload(row["Название"]),
                "width_m": None,
                "length_m": None,
                "turning_radius_m": None,
                "attributes": {
                    "source_category": row["тип"].strip() or None,
                    "source_rows": [row_number],
                    "has_source_id_variants": has_variants,
                },
                "source_row_number": row_number,
                "data_completeness": round(present / len(row), 3),
                "source_status": "source_present",
                "source_name": "catalog_export_v4.csv",
                "source_date": "2026-09-20",
            },
        )
        if row_number not in product["attributes"]["source_rows"]:
            product["attributes"]["source_rows"].append(row_number)
        if row["Кейсы"].strip():
            cases.append(
                {
                    "id": f"case-{row_number - 1:03d}-{source_id}",
                    "solution_id": solution_id,
                    "summary": row["Кейсы"].strip(),
                    "source_name": "catalog_export_v4.csv",
                }
            )
    return {
        "families": list(families.values()),
        "products": list(products.values()),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-only", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog(INPUT / "catalog_export_v4.csv")
    if not args.catalog_only:
        object_types = build_object_types(INPUT / "Датасеты_хакатон.xlsx")
        (OUTPUT / "object_types.json").write_text(
            json.dumps(object_types, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (OUTPUT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "Создан каталог: "
        f"{len(catalog['families'])} семейств, {len(catalog['products'])} конфигураций, "
        f"{len(catalog['cases'])} кейсов."
    )


if __name__ == "__main__":
    main()
