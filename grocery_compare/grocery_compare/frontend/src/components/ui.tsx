// Small shared UI pieces: badges, banners, skeletons, empty state, toasts.
import type { ReactNode } from "react";
import { toastStore } from "../store";
import type { StoreName } from "../types";

export function StoreBadge({ store }: { store: StoreName }) {
  const cls = store === "BigBasket" ? "bg-bb/15 text-lime-800 dark:text-lime-300" : "bg-jm/15 text-sky-800 dark:text-sky-300";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{store}</span>;
}

export function Banner({ kind = "warn", children }: { kind?: "warn" | "error" | "info"; children: ReactNode }) {
  const cls = {
    warn: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/50 dark:text-amber-200",
    error: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200",
    info: "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-200",
  }[kind];
  return <div role={kind === "error" ? "alert" : "status"} className={`rounded-xl border px-4 py-3 text-sm ${cls}`}>{children}</div>;
}

export const Card = ({ className = "", children }: { className?: string; children: ReactNode }) => (
  <div className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}>
    {children}
  </div>
);

export function Loader({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-500" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-500" />
      {label}
    </div>
  );
}

export function RowSkeleton() {
  return (
    <div className="flex animate-pulse gap-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="size-16 rounded-lg bg-slate-200 dark:bg-slate-800" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-2/3 rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-3 w-1/4 rounded bg-slate-200 dark:bg-slate-800" />
      </div>
      <div className="hidden w-48 gap-3 sm:flex">
        <div className="h-14 flex-1 rounded-lg bg-slate-200 dark:bg-slate-800" />
        <div className="h-14 flex-1 rounded-lg bg-slate-200 dark:bg-slate-800" />
      </div>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center dark:border-slate-700">
      <div className="text-4xl">🧺</div>
      <h2 className="mt-2 font-semibold">{title}</h2>
      <div className="mt-1 text-sm text-slate-500">{children}</div>
    </div>
  );
}

export function Toaster() {
  const toasts = toastStore.use();
  return (
    <div className="fixed right-4 bottom-4 z-50 flex max-w-sm flex-col gap-2" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`rounded-xl px-4 py-3 text-sm text-white shadow-lg ${t.kind === "error" ? "bg-red-600" : "bg-slate-800 dark:bg-slate-700"}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
