import { useQuery } from "@tanstack/react-query";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Database, Search } from "lucide-react";
import { useState } from "react";
import { Badge, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import { money, statusLabel } from "../lib/format";
import type { Solution } from "../types";

const column = createColumnHelper<Solution>();
const columns = [
  column.accessor("name", { header: "Решение", cell: (info) => <div className="product-name"><b>{info.getValue()}</b><span>{info.row.original.manufacturer}</span></div> }),
  column.accessor("catalog_type", { header: "Тип", cell: (info) => info.getValue() ?? "Не указан" }),
  column.accessor("status", { header: "Стадия", cell: (info) => <Badge tone={info.getValue() === "operation" ? "success" : "neutral"}>{statusLabel[info.getValue()] ?? info.getValue()}</Badge> }),
  column.accessor("trl", { header: "УГТ", cell: (info) => info.getValue() ? `${info.getValue()}/9` : "—" }),
  column.accessor("price_rub", { header: "Цена", cell: (info) => money(info.getValue()) }),
  column.accessor("data_completeness", { header: "Полнота", cell: (info) => <div className="completeness"><i style={{ width: `${info.getValue() * 100}%` }} /><span>{Math.round(info.getValue() * 100)}%</span></div> }),
];

export function CatalogPage() {
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["catalog", search],
    queryFn: () => api<{ count: number; items: Solution[]; source: string }>(`/catalog?limit=60&search=${encodeURIComponent(search)}`),
  });
  const table = useReactTable({ data: query.data?.items ?? [], columns, getCoreRowModel: getCoreRowModel() });
  return (
    <section className="page page-wide catalog-page">
      <div className="page-header"><div><p className="section-kicker">Подтверждено конкурсным источником</p><h1>Каталог решений</h1><p>187 уникальных продуктов отделены от 223 строк внедрений; неизвестные характеристики не заполняются догадками.</p></div><div className="catalog-stat"><Database /><b>{query.data?.count ?? 187}</b><span>найдено</span></div></div>
      <div className="catalog-tools"><label><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Название или производитель" /></label><Badge tone="source">Источник: catalog_export_v4.csv</Badge></div>
      {query.isLoading && <Loading />}{query.error && <ErrorState message={query.error.message} />}
      {query.data && <div className="table-wrap"><table><thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map((row) => <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table></div>}
    </section>
  );
}
