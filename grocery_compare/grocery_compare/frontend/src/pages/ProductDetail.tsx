import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import Plot from "../components/Plot";
import { Banner, Card, Loader, StoreBadge } from "../components/ui";
import { STORE_COLOR, asDate, packLabel, rupee, unitSuffix, when } from "../format";
import { addToBasket } from "../store";
import type { HistoryPoint, Product, StoreName } from "../types";

const RANGES = [7, 30, 90];

function series(history: HistoryPoint[], y: (p: HistoryPoint) => number, extra: object = {}) {
  const stores = [...new Set(history.map((p) => p.store))] as StoreName[];
  return stores.map((store) => {
    const pts = history.filter((p) => p.store === store);
    return { type: "scatter", mode: "lines+markers", name: store, x: pts.map((p) => asDate(p.scraped_at)), y: pts.map(y),
      line: { color: STORE_COLOR[store], shape: "hv" }, ...extra };
  });
}

function ProductCard({ p }: { p: Product }) {
  return (
    <Card className="flex gap-4">
      {p.image_url && <img src={p.image_url} alt="" className="size-20 rounded-lg bg-white object-contain" />}
      <div className="min-w-0 space-y-1">
        <StoreBadge store={p.store} />
        <div className="font-medium">{p.name}</div>
        <div className="text-sm">
          <b className="text-lg">{rupee(p.price, 2)}</b>
          {p.mrp > p.price && <span className="ml-2 text-slate-400 line-through">{rupee(p.mrp, 2)}</span>}
          {p.discount_pct > 0 && <span className="ml-2 text-emerald-700 dark:text-emerald-400">{p.discount_pct}% off</span>}
        </div>
        <div className="text-xs text-slate-500">
          {packLabel(p.pack_qty_base, p.pack_kind)} {p.unit_price != null && `· ${rupee(p.unit_price, 2)}${unitSuffix(p.pack_kind)}`} · {when(p.scraped_at)}
        </div>
        <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-sm text-emerald-700 underline dark:text-emerald-400">Open on {p.store} ↗</a>
      </div>
    </Card>
  );
}

export default function ProductDetail() {
  const id = Number(useParams().id);
  const [days, setDays] = useState(30);
  const { data, error, isPending } = useQuery({ queryKey: ["history", id, days], queryFn: () => api.history(id, days), enabled: id > 0 });
  const priceData = useMemo(() => (data ? series(data.history, (p) => p.price) : []), [data]);
  const discountData = useMemo(() => (data ? series(data.history, (p) => p.discount_pct) : []), [data]);

  if (error) return <div className="py-6"><Banner kind="error">{error.message}</Banner></div>;
  if (isPending || !data) return <div className="py-10"><Loader /></div>;

  const { product, counterpart } = data;
  const [bb, jm] = product.store === "BigBasket" ? [product, counterpart] : [counterpart, product];
  const basketEntry = counterpart
    ? { key: `p${product.id}`, product_ids: [product.id, counterpart.id], name: product.name, image_url: product.image_url }
    : { key: `p${product.id}`, product_ids: [product.id], name: product.name, image_url: product.image_url };

  return (
    <div className="space-y-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 className="text-2xl font-bold">{product.name}</h1>
        <button onClick={() => addToBasket(basketEntry)} className="rounded-xl bg-emerald-600 px-4 py-2 font-semibold text-white">+ Add to basket</button>
      </div>
      {!counterpart && <Banner kind="info">Not matched to a product on the other store yet.</Banner>}
      {counterpart && data.match_score != null && (
        <p className="text-sm text-slate-500">Matched with {counterpart.store} listing (match score {Math.round(data.match_score * 100)}%).</p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {bb && <ProductCard p={bb} />}
        {jm && <ProductCard p={jm} />}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {data.stats.map((s) => (
          <Card key={s.store}>
            <StoreBadge store={s.store} /> <span className="text-xs text-slate-500">last {days} days</span>
            <dl className="mt-2 grid grid-cols-4 gap-2 text-center text-sm">
              {([["Lowest", s.lowest], ["Highest", s.highest], ["Average", s.average], ["Current", s.current]] as const).map(([k, v]) => (
                <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="font-semibold">{rupee(v, 2)}</dd></div>
              ))}
            </dl>
          </Card>
        ))}
      </div>

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Price history</h2>
          <div className="flex gap-1 text-sm" role="group" aria-label="Date range">
            {RANGES.map((d) => (
              <button key={d} onClick={() => setDays(d)} aria-pressed={d === days}
                className={`rounded-lg px-3 py-1 ${d === days ? "bg-emerald-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>{d}d</button>
            ))}
          </div>
        </div>
        {data.history.length < 2 && (
          <p className="mb-2 text-sm text-slate-500">Only one price so far. History builds up as the scheduler re-scrapes popular items every 12 hours.</p>
        )}
        <Plot data={priceData} layout={{ yaxis: { title: { text: "Price (₹)" } } }} />
      </Card>
      <Card>
        <h2 className="mb-2 font-semibold">Discount history (% off MRP)</h2>
        <Plot data={discountData} height={240} layout={{ yaxis: { title: { text: "% off" } } }} />
      </Card>
    </div>
  );
}
