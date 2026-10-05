import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { CompareRow, ProductRow } from "../components/CompareRow";
import { Banner, EmptyState, RowSkeleton } from "../components/ui";
import { STORE_NAME, rupee, when } from "../format";
import { pincodeStore } from "../store";
import type { MatchRow, Product, SearchResponse, StoreKey } from "../types";

type Sort = "cheapest" | "saving" | "unit_price" | "name";
interface Filters { sort: Sort; store: StoreKey | "all"; min: string; max: string; brands: string[]; inStock: boolean }
const NO_FILTERS: Filters = { sort: "cheapest", store: "all", min: "", max: "", brands: [], inStock: false };

const best = (r: MatchRow) => Math.min(r.bigbasket.price, r.jiomart.price);

function applyFilters(data: SearchResponse, f: Filters) {
  const min = f.min ? Number(f.min) : -Infinity;
  const max = f.max ? Number(f.max) : Infinity;
  const brandOk = (...ps: Product[]) => !f.brands.length || ps.some((p) => p.brand && f.brands.includes(p.brand));
  const rowKey: Record<Sort, (r: MatchRow) => number | string> = {
    cheapest: best, saving: (r) => -r.saving_abs, name: (r) => r.bigbasket.name.toLowerCase(),
    unit_price: (r) => Math.min(r.bigbasket.unit_price ?? 1e9, r.jiomart.unit_price ?? 1e9),
  };
  const prodKey: Record<Sort, (p: Product) => number | string> = {
    cheapest: (p) => p.price, saving: (p) => p.price, name: (p) => p.name.toLowerCase(), unit_price: (p) => p.unit_price ?? 1e9,
  };
  const by = <T,>(key: (x: T) => number | string) => (a: T, b: T) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0);
  const prods = (list: Product[], store: StoreKey) =>
    f.store !== "all" && f.store !== store ? [] :
      list.filter((p) => p.price >= min && p.price <= max && brandOk(p) && (!f.inStock || p.in_stock)).sort(by(prodKey[f.sort]));
  return {
    matched: data.matched
      .filter((r) => best(r) >= min && best(r) <= max && brandOk(r.bigbasket, r.jiomart)
        && (!f.inStock || r.bigbasket.in_stock || r.jiomart.in_stock))
      .sort(by(rowKey[f.sort])),
    only_bigbasket: prods(data.only_bigbasket, "bigbasket"),
    only_jiomart: prods(data.only_jiomart, "jiomart"),
  };
}

function FiltersBar({ f, set, brands }: { f: Filters; set: (f: Filters) => void; brands: string[] }) {
  const input = "rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900";
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <select aria-label="Sort" className={input} value={f.sort} onChange={(e) => set({ ...f, sort: e.target.value as Sort })}>
        <option value="cheapest">Cheapest first</option>
        <option value="saving">Biggest saving</option>
        <option value="unit_price">Unit price</option>
        <option value="name">Name</option>
      </select>
      <select aria-label="Store" className={input} value={f.store} onChange={(e) => set({ ...f, store: e.target.value as Filters["store"] })}>
        <option value="all">Both stores</option>
        <option value="bigbasket">BigBasket</option>
        <option value="jiomart">JioMart</option>
      </select>
      <input aria-label="Min price" className={`${input} w-20`} type="number" min={0} placeholder="Min ₹" value={f.min} onChange={(e) => set({ ...f, min: e.target.value })} />
      <input aria-label="Max price" className={`${input} w-20`} type="number" min={0} placeholder="Max ₹" value={f.max} onChange={(e) => set({ ...f, max: e.target.value })} />
      {brands.length > 1 && (
        <details className="relative">
          <summary className={`${input} cursor-pointer list-none`}>Brands{f.brands.length ? ` (${f.brands.length})` : ""} ▾</summary>
          <div className="absolute z-10 mt-1 max-h-64 w-52 overflow-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            {brands.map((b) => (
              <label key={b} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                <input type="checkbox" checked={f.brands.includes(b)}
                  onChange={(e) => set({ ...f, brands: e.target.checked ? [...f.brands, b] : f.brands.filter((x) => x !== b) })} />
                {b}
              </label>
            ))}
          </div>
        </details>
      )}
      <label className="flex items-center gap-1.5">
        <input type="checkbox" checked={f.inStock} onChange={(e) => set({ ...f, inStock: e.target.checked })} /> In stock only
      </label>
      {JSON.stringify(f) !== JSON.stringify(NO_FILTERS) && (
        <button onClick={() => set(NO_FILTERS)} className="text-emerald-700 underline dark:text-emerald-400">Reset</button>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: Product[] }) {
  if (!items.length) return null;
  return (
    <details open className="group space-y-3">
      <summary className="cursor-pointer text-lg font-semibold">{title} <span className="text-sm font-normal text-slate-500">({items.length})</span></summary>
      <div className="mt-3 space-y-3">{items.map((p) => <ProductRow key={p.id} p={p} />)}</div>
    </details>
  );
}

export default function SearchResults() {
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const storePin = pincodeStore.use();
  const pincode = params.get("pincode") ?? storePin;
  const [refresh, setRefresh] = useState(0);
  const [filters, setFilters] = useState(NO_FILTERS);
  const valid = q.length >= 2 && q.length <= 60 && /^\d{6}$/.test(pincode);

  // pincode changed from the navbar while on this page -> search again for the new pincode
  const firstPin = useRef(true);
  useEffect(() => {
    if (firstPin.current) { firstPin.current = false; return; }
    setParams((p) => { p.set("pincode", storePin); return p; });
  }, [storePin, setParams]);
  useEffect(() => setFilters(NO_FILTERS), [q]);

  // 1) start (or reuse) a background scrape  2) poll it  3) read results from the DB
  const start = useQuery({
    queryKey: ["scrape", q, pincode, refresh],
    queryFn: () => api.startScrape(q, pincode, refresh > 0),
    enabled: valid, staleTime: Infinity, retry: false,
  });
  const poll = useQuery({
    queryKey: ["job", start.data?.run_id],
    queryFn: () => api.scrapeStatus(start.data!.run_id),
    enabled: start.data?.status === "running",
    refetchInterval: (query) => (query.state.data && query.state.data.status !== "running" ? false : 1500),
    retry: false,
  });
  const job = poll.data?.run_id === start.data?.run_id ? poll.data : start.data;
  const done = !!job && job.status !== "running";
  const results = useQuery({
    queryKey: ["search", q, pincode, job?.run_id],
    queryFn: () => api.search(q, pincode),
    enabled: done,
  });

  const data = results.data;
  const view = useMemo(() => (data ? applyFilters(data, filters) : null), [data, filters]);
  const brands = useMemo(() => {
    if (!data) return [];
    const all = [...data.matched.flatMap((r) => [r.bigbasket, r.jiomart]), ...data.only_bigbasket, ...data.only_jiomart];
    return [...new Set(all.map((p) => p.brand).filter((b): b is string => !!b))].sort();
  }, [data]);

  if (!valid) return <EmptyState title="Type at least 2 characters to search">Pincode must be 6 digits.</EmptyState>;

  const error = start.error ?? poll.error ?? results.error;
  const total = data ? data.matched.length * 2 + data.only_bigbasket.length + data.only_jiomart.length : 0;
  const wins = (k: StoreKey) => data?.matched.filter((r) => r.cheaper === k).length ?? 0;
  const avgSaving = data?.matched.length ? data.matched.reduce((s, r) => s + r.saving_abs, 0) / data.matched.length : 0;

  return (
    <div className="space-y-5 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Results for “{q}”</h1>
          <p className="text-sm text-slate-500">
            Pincode {pincode}{data?.scraped_at && <> · prices from {when(data.scraped_at)}</>}
          </p>
        </div>
        {data && (
          <div className="flex gap-2 text-sm">
            <button onClick={() => setRefresh(Date.now())} disabled={!done}
              className="rounded-xl border border-slate-300 px-3 py-1.5 disabled:opacity-40 dark:border-slate-700" title="Scrape again, ignoring the 6-hour cache">
              ↻ Refresh prices
            </button>
            <a href={api.csvUrl(q, pincode)} className="rounded-xl border border-slate-300 px-3 py-1.5 dark:border-slate-700">⬇ CSV</a>
          </div>
        )}
      </div>

      {error && <Banner kind="error">{error.message}</Banner>}
      {job?.status === "error" && <Banner kind="error">{job.messages.at(-1)}</Banner>}
      {data?.warnings.map((w) => <Banner key={w}>{w}</Banner>)}

      {!data && !error && (
        <div className="space-y-3">
          <Banner kind="info">
            {job?.messages.at(-1) ?? "Starting search..."}
            <span className="ml-1 text-xs opacity-70">Live scraping takes 10-60 seconds.</span>
          </Banner>
          {Array.from({ length: 4 }, (_, i) => <RowSkeleton key={i} />)}
        </div>
      )}

      {data && view && (
        total === 0 ? (
          <EmptyState title="No products found">Neither store returned results for “{q}”. Try a simpler term like “milk” or “atta”.</EmptyState>
        ) : (
          <>
            <div className="rounded-xl bg-emerald-50 px-4 py-2 text-sm text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
              Found <b>{total}</b> products · <b>{data.matched.length}</b> on both stores
              {data.matched.length > 0 && <>
                {" "}· {STORE_NAME.jiomart} cheaper on <b>{wins("jiomart")}</b> · {STORE_NAME.bigbasket} cheaper on <b>{wins("bigbasket")}</b>
                {" "}· avg saving <b>{rupee(avgSaving, 2)}</b>
              </>}
            </div>
            <FiltersBar f={filters} set={setFilters} brands={brands} />
            {view.matched.length > 0 && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold">On both stores</h2>
                {view.matched.map((r) => <CompareRow key={r.match_id} row={r} />)}
              </section>
            )}
            <Section title="Only on BigBasket" items={view.only_bigbasket} />
            <Section title="Only on JioMart" items={view.only_jiomart} />
            {!view.matched.length && !view.only_bigbasket.length && !view.only_jiomart.length &&
              <EmptyState title="Nothing matches these filters" />}
          </>
        )
      )}
    </div>
  );
}
