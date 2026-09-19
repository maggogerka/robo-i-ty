import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

type Sensitivity = {
  factor: string;
  points: { change_percent: number; payback_years: number | null }[];
};

export function SensitivityChart({ data }: { data: Sensitivity[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      tooltip: { trigger: "axis", valueFormatter: (value: unknown) => `${value ?? "—"} года` },
      legend: { bottom: 0, textStyle: { color: "#526575" } },
      grid: { left: 48, right: 18, top: 20, bottom: 58 },
      xAxis: { type: "category", data: ["−20%", "База", "+20%"], axisLine: { lineStyle: { color: "#ccd9df" } } },
      yAxis: { type: "value", name: "Окупаемость, лет", splitLine: { lineStyle: { color: "#e8eff2" } } },
      series: data.map((item, index) => ({
        name: item.factor,
        type: "line",
        smooth: true,
        symbolSize: 9,
        lineStyle: { width: 3 },
        itemStyle: { color: ["#067a73", "#195b88", "#d77836"][index] },
        data: item.points.map((point) => point.payback_years),
      })),
    });
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.dispose(); };
  }, [data]);
  return <div ref={ref} className="chart" role="img" aria-label="Чувствительность срока окупаемости" />;
}
