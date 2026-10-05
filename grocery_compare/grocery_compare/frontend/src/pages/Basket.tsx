import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Banner, Card, EmptyState, Loader } from "../components/ui";
import { STORE_NAME, rupee } from "../format";
import { basketStore, pincodeStore, removeFromBasket, setQty } from "../store";
import type { BasketResponse, StoreKey } from "../types";

const KEYS: StoreKey[] = ["bigbasket", "jiomart"];

function downloadCsv(res: BasketResponse) {
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const rows = [["item", "qty", "bigbasket", "jiomart", "best_store"], ...res.lines.map((l) => [l.name, l.qty, l.bigbasket, l.jiomart, l.best_store]),
    [], ["total", "", res.totals.bigbasket, res.totals.jiomart, ""], ["best split total", "", "", "", res.best_split_total]];
  const url = URL.createObjectURL(new Blob([rows.map((r) => r.map(esc).join(",")).join("\n")], { type: "text/csv" }));
  Object.assign(document.createElement("a"), { href: url, download: "basket.csv" }).click();
  URL.revokeObjectURL(url);
}

export default function Basket() {
  const items = basketStore.use();
  const pincode = pincodeStore.use();
  const payload = items.map(({ match_id, product_ids, qty }) => ({ match_id, product_ids, qty }));
  const { data, error, isFetching } = useQuery({
    queryKey: ["basket", payload, pincode],
    queryFn: () => api.basket(payload, pincode),
    enabled: items.length > 0,
    placeholderData: keepPreviousData,
  });

  if (!items.length) {
    return <div className="py-10"><EmptyState title="Your basket is empty">Add items from <Link to="/" className="underline">a search</Link> to compare totals.</EmptyState></div>;
  }

  const saving = data?.saving_vs_worst_single;
  return (
    <div className="space-y-6 py-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Basket <span className="text-base font-normal text-slate-500">· pincode {pincode}</span></h1>
        <div className="flex gap-2 text-sm">
          {data && <button onClick={() => downloadCsv(data)} className="rounded-xl border border-slate-300 px-3 py-1.5 dark:border-slate-700">⬇ CSV</button>}
          <button onClick={() => basketStore.set([])} className="rounded-xl border border-red-300 px-3 py-1.5 text-red-700 dark:border-red-800 dark:text-red-400">Clear basket</button>
        </div>
      </div>
      {error && <Banner kind="error">{error.message}</Banner>}

      {data && (
        <div className="grid gap-4 md:grid-cols-3">
          {KEYS.map((k) => (
            <Card key={k}>
              <div className="text-sm text-slate-500">All on {STORE_NAME[k]}</div>
              <div className="text-2xl font-bold">{data.missing[k] === data.lines.length ? "n/a" : rupee(data.totals[k], 2)}</div>
              {data.missing[k] > 0 && data.missing[k] < data.lines.length &&<div className="text-xs text-amber-700 dark:text-amber-400">{data.missing[k]} item(s) not available, total incomplete</div>}
            </Card>
          ))}
          <Card className="border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40">
            <div className="text-sm text-emerald-800 dark:text-emerald-300">Best split</div>
            <div className="text-2xl font-bold">{rupee(data.best_split_total, 2)}</div>
            {saving != null && saving > 0 && <div className="text-3xl font-extrabold text-emerald-600">save {rupee(saving, 2)}</div>}
          </Card>
        </div>
      )}

      {data && KEYS.every((k) => data.best_split[k].length > 0) && (
        <Banner kind="info">
          Buy <b>{data.best_split.jiomart.join(", ")}</b> on JioMart and <b>{data.best_split.bigbasket.join(", ")}</b> on BigBasket
          {data.saving_vs_best_single != null && data.saving_vs_best_single > 0 && <> to save {rupee(data.saving_vs_best_single, 2)} vs. the cheapest single store</>}.
        </Banner>
      )}

      <div className="space-y-3">
        {items.map((item, i) => {
          const line = data?.lines[i];
          return (
            <Card key={item.key} className="flex flex-wrap items-center gap-4">
              {item.image_url ? <img src={item.image_url} alt="" className="size-14 rounded-lg bg-white object-contain" /> : <div className="size-14 text-3xl">🛍️</div>}
              <div className="min-w-0 flex-1 font-medium">{item.name}</div>
              <div className="flex items-center rounded-xl border border-slate-300 dark:border-slate-700">
                <button aria-label="Decrease quantity" onClick={() => setQty(item.key, item.qty - 1)} className="px-3 py-1">−</button>
                <span className="w-8 text-center">{item.qty}</span>
                <button aria-label="Increase quantity" onClick={() => setQty(item.key, item.qty + 1)} className="px-3 py-1">+</button>
              </div>
              <div className="flex gap-3 text-sm">
                {KEYS.map((k) => (
                  <div key={k} className={`w-24 rounded-lg px-2 py-1 text-center ${line?.best_store === k ? "bg-emerald-100 font-semibold dark:bg-emerald-900" : ""}`}>
                    <div className="text-xs text-slate-500">{STORE_NAME[k]}</div>
                    {line ? (line[k] == null ? <span className="text-slate-400">n/a</span> : rupee(line[k], 2)) : "…"}
                  </div>
                ))}
              </div>
              <button onClick={() => removeFromBasket(item.key)} aria-label="Remove item" className="text-slate-400 hover:text-red-600">✕</button>
            </Card>
          );
        })}
      </div>
      {isFetching && <Loader label="Updating totals..." />}
    </div>
  );
}
