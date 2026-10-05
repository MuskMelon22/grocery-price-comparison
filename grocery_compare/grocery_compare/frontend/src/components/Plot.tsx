// Plotly.js wrapper. Plotly is ~3.5 MB, so it's loaded lazily only on pages with charts.
import { useEffect, useRef } from "react";
import { themeStore } from "../store";

type Plotly = typeof import("plotly.js-dist-min").default;
let plotly: Plotly | null = null; // cached so unmount can purge synchronously (an async purge races StrictMode remounts)
const loadPlotly = () => import("plotly.js-dist-min").then((m) => (plotly = m.default));

type Props = { data: object[]; layout?: Record<string, unknown>; height?: number };

export default function Plot({ data, layout = {}, height = 320 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const theme = themeStore.use();

  useEffect(() => {
    let cancelled = false;
    loadPlotly().then((Plotly) => {
      if (cancelled || !ref.current) return;
      const text = theme === "dark" ? "#cbd5e1" : "#334155";
      const grid = theme === "dark" ? "#1e293b" : "#e2e8f0";
      Plotly.react(ref.current, data, {
        height,
        margin: { t: 20, r: 10, b: 40, l: 50 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: text, family: "inherit" },
        legend: { orientation: "h", y: -0.2 },
        ...layout,
        xaxis: { gridcolor: grid, ...(layout.xaxis as object) },
        yaxis: { gridcolor: grid, ...(layout.yaxis as object) },
      }, { responsive: true, displayModeBar: false });
    });
    return () => { cancelled = true; };
  }, [data, layout, height, theme]);

  useEffect(() => {
    const el = ref.current;
    return () => { if (el && plotly) plotly.purge(el); };
  }, []);

  return <div ref={ref} style={{ minHeight: height }} className="w-full" />;
}
