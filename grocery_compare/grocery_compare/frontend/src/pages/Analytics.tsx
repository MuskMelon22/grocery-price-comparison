import { useQuery } from "@tanstack/react-query";
import { useMemo, type ReactNode } from "react";
import { api } from "../api/client";
import Plot from "../components/Plot";
import { Banner, Card, EmptyState, Loader } from "../components/ui";
import { STORE_COLOR, when } from "../format";
import type { StoreName } from "../types";

const STORES: StoreName[] = ["BigBasket", "JioMart"];
const pct = (v: number | null) => (v == null ? "–" : `${v}%`);

const Stat = ({ label, children }: { label: string; children: ReactNode }) => (
  <Card><div className="text-xs text-slate-500">{label}</div><div className="mt-1 text-xl font-bold">{children}</div></Card>
);

const ChartCard = ({ title, children }: { title: string; children: ReactNode }) => (
  <Card><h2 className="mb-2 font-semibold">{title}</h2>{children}</Card>
);

export default function Analytics() {
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary });
  const disc = useQuery({ queryKey: ["discounts"], queryFn: api.discounts });
  const s = summary.data;

  const charts = useMemo(() => {
    if (!s) return null;
    return {
      win: [{ type: "pie", hole: 0.55, labels: [...STORES, "Same price"],
        values: [s.win_rate.BigBasket, s.win_rate.JioMart, s.ties_pct],
        marker: { colors: [STORE_COLOR.BigBasket, STORE_COLOR.JioMart, "#94a3b8"] } }],
      category: STORES.map((st) => ({ type: "bar", name: st, marker: { color: STORE_COLOR[st] },
        x: s.category_comparison.map((c) => c.category), y: s.category_comparison.map((c) => c[st]) })),
      gaps: [{ type: "bar", orientation: "h", x: [...s.top_gaps].reverse().map((g) => g.gap),
        y: [...s.top_gaps].reverse().map((g) => g.name.slice(0, 40)),
        marker: { color: [...s.top_gaps].reverse().map((g) => STORE_COLOR[g.cheaper as StoreName] ?? "#94a3b8") },
        hovertemplate: "₹%{x} gap<extra></extra>" }],
      trend: STORES.map((st) => {
        const pts = s.trend.filter((t) => t.store === st);
        return { type: "scatter", mode: "lines+markers", name: st, x: pts.map((t) => t.day), y: pts.map((t) => t.unit_price),
          line: { color: STORE_COLOR[st] } };
      }),
    };
  }, [s]);
  const box = useMemo(() => STORES.map((st) => ({ type: "box", name: st, y: disc.data?.[st] ?? [],
    marker: { color: STORE_COLOR[st] }, boxpoints: "all", jitter: 0.4 })), [disc.data]);

  if (summary.error) return <div className="py-6"><Banner kind="error">{summary.error.message}</Banner></div>;
  if (!s || !charts) return <div className="py-10"><Loader /></div>;
  if (!s.snapshots) return <div className="py-10"><EmptyState title="No data yet">Run a few searches (or <code>python seed_scrape.py</code>) first.</EmptyState></div>;

  return (
    <div className="space-y-6 py-6">
      <h1 className="text-2xl font-bold">Analytics</h1>
      {s.matched_pairs === 0 && <Banner>No products matched across both stores yet (e.g. one store blocked the scraper), so store-vs-store charts are empty.</Banner>}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Products tracked">{s.products_tracked}</Stat>
        <Stat label="Price snapshots">{s.snapshots}</Stat>
        <Stat label="Matched pairs">{s.matched_pairs}</Stat>
        <Stat label="Avg / median price gap">{pct(s.avg_price_diff_pct)} / {pct(s.median_price_diff_pct)}</Stat>
        {STORES.map((st) => <Stat key={st} label={`${st} avg discount`}>{pct(s.avg_discount[st])}</Stat>)}
        {STORES.map((st) => <Stat key={st} label={`${st} price volatility (σ ₹)`}>{s.volatility[st] ?? "–"}</Stat>)}
      </div>
      <p className="text-xs text-slate-500">Last scrape: {STORES.map((st) => `${st} ${when(s.last_scrape[st])}`).join(" · ")}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Who is cheaper (matched products)"><Plot data={charts.win} /></ChartCard>
        <ChartCard title="Median unit price by category (₹ per 100 g/ml or item)">
          <Plot data={charts.category} layout={{ barmode: "group" }} />
        </ChartCard>
        <ChartCard title="Discount distribution (% off MRP)"><Plot data={box} /></ChartCard>
        <ChartCard title="Top 10 price gaps (colour = cheaper store)">
          <Plot data={charts.gaps} layout={{ margin: { l: 220, r: 10, t: 10, b: 40 } }} />
        </ChartCard>
      </div>
      <ChartCard title="Price trend (daily median unit price)"><Plot data={charts.trend} /></ChartCard>
    </div>
  );
}
