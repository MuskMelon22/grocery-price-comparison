import { Link } from "react-router-dom";
import { STORE_NAME, packLabel, rupee, unitSuffix } from "../format";
import { addToBasket } from "../store";
import type { MatchRow, Product } from "../types";
import { StoreBadge } from "./ui";

function Thumb({ p }: { p: Product }) {
  return p.image_url
    ? <img src={p.image_url} alt="" loading="lazy" className="size-16 shrink-0 rounded-lg bg-white object-contain" />
    : <div className="grid size-16 shrink-0 place-items-center rounded-lg bg-slate-100 text-2xl dark:bg-slate-800">🛍️</div>;
}

function PriceCell({ p, best }: { p: Product; best: boolean }) {
  return (
    <a href={p.url} target="_blank" rel="noopener noreferrer" title={`Open on ${p.store}`}
      className={`block flex-1 rounded-xl border p-3 transition hover:shadow ${best ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40" : "border-slate-200 dark:border-slate-800"}`}>
      <div className="flex items-center justify-between gap-2">
        <StoreBadge store={p.store} />
        {best && <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400">Best price</span>}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-xl font-bold">{rupee(p.price, 2)}</span>
        {p.mrp > p.price && <span className="text-xs text-slate-400 line-through">{rupee(p.mrp, 2)}</span>}
        {p.discount_pct > 0 && <span className="text-xs text-emerald-700 dark:text-emerald-400">{p.discount_pct}% off</span>}
      </div>
      <div className="text-xs text-slate-500">
        {p.unit_price != null && `${rupee(p.unit_price, 2)}${unitSuffix(p.pack_kind)}`}
        {!p.in_stock && <span className="ml-2 font-semibold text-red-600">Out of stock</span>}
      </div>
    </a>
  );
}

const AddButton = ({ onClick }: { onClick: () => void }) => (
  <button onClick={onClick} className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold whitespace-nowrap text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900">
    + Basket
  </button>
);

export function CompareRow({ row }: { row: MatchRow }) {
  const { bigbasket: bb, jiomart: jm } = row;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex gap-4">
        <Thumb p={bb.image_url ? bb : jm} />
        <div className="min-w-0 flex-1">
          <Link to={`/product/${bb.id}`} className="line-clamp-2 font-medium hover:underline">{bb.name}</Link>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            {packLabel(bb.pack_qty_base, bb.pack_kind) && <span>{packLabel(bb.pack_qty_base, bb.pack_kind)}</span>}
            <span title="How closely the two store listings match">match {Math.round(row.match_score * 100)}%</span>
          </div>
          <div className="mt-2 text-sm">
            {row.cheaper
              ? <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
                  Cheaper on {STORE_NAME[row.cheaper]}, save {rupee(row.saving_abs, 2)} ({row.saving_pct}%)
                </span>
              : <span className="text-slate-500">Same price on both</span>}
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-stretch">
        <PriceCell p={bb} best={row.cheaper === "bigbasket"} />
        <PriceCell p={jm} best={row.cheaper === "jiomart"} />
        <div className="flex items-center sm:justify-end">
          <AddButton onClick={() => addToBasket({ key: `m${row.match_id}`, match_id: row.match_id, name: bb.name, image_url: bb.image_url ?? jm.image_url })} />
        </div>
      </div>
    </div>
  );
}

export function ProductRow({ p }: { p: Product }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center dark:border-slate-800 dark:bg-slate-900">
      <div className="flex min-w-0 flex-1 gap-4">
        <Thumb p={p} />
        <div className="min-w-0">
          <Link to={`/product/${p.id}`} className="line-clamp-2 font-medium hover:underline">{p.name}</Link>
          <div className="mt-1 text-xs text-slate-500">{packLabel(p.pack_qty_base, p.pack_kind)}</div>
        </div>
      </div>
      <div className="flex items-center gap-3 sm:w-80">
        <PriceCell p={p} best={false} />
        <AddButton onClick={() => addToBasket({ key: `p${p.id}`, product_ids: [p.id], name: p.name, image_url: p.image_url })} />
      </div>
    </div>
  );
}
