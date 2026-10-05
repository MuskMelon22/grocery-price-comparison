// Tiny shared stores (pincode, basket, theme, toasts) on useSyncExternalStore; persisted ones use localStorage.
import { useSyncExternalStore } from "react";

function createStore<T>(initial: T, storageKey?: string) {
  let state = initial;
  if (storageKey) {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) state = JSON.parse(raw) as T;
    } catch { /* private mode / bad JSON: keep default */ }
  }
  const subs = new Set<() => void>();
  const subscribe = (cb: () => void) => {
    subs.add(cb);
    return () => { subs.delete(cb); };
  };
  return {
    get: () => state,
    set(next: T | ((prev: T) => T)) {
      state = typeof next === "function" ? (next as (prev: T) => T)(state) : next;
      if (storageKey) {
        try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* ignore */ }
      }
      subs.forEach((f) => f());
    },
    use: (): T => useSyncExternalStore(subscribe, () => state),
  };
}

// --- pincode ---
export const pincodeStore = createStore("400001", "pincode");

// --- basket ---
export interface BasketEntry {
  key: string; // "m<matchId>" or "p<productId>", dedupes adds
  name: string;
  image_url: string | null;
  qty: number;
  match_id?: number;
  product_ids?: number[];
}
export const basketStore = createStore<BasketEntry[]>([], "basket");

export function addToBasket(entry: Omit<BasketEntry, "qty">) {
  basketStore.set((items) =>
    items.some((i) => i.key === entry.key)
      ? items.map((i) => (i.key === entry.key ? { ...i, qty: Math.min(i.qty + 1, 99) } : i))
      : [...items, { ...entry, qty: 1 }],
  );
  toast(`Added "${entry.name.slice(0, 40)}" to basket`);
}
export const setQty = (key: string, qty: number) =>
  basketStore.set((items) => items.map((i) => (i.key === key ? { ...i, qty: Math.max(1, Math.min(qty, 99)) } : i)));
export const removeFromBasket = (key: string) => basketStore.set((items) => items.filter((i) => i.key !== key));

// --- theme ---
export const themeStore = createStore<"light" | "dark">(
  document.documentElement.classList.contains("dark") ? "dark" : "light",
);
export function toggleTheme() {
  const next = themeStore.get() === "dark" ? "light" : "dark";
  document.documentElement.classList.toggle("dark", next === "dark");
  try { localStorage.setItem("theme", next); } catch { /* ignore */ }
  themeStore.set(next);
}

// --- toasts ---
export interface Toast { id: number; text: string; kind: "info" | "error" }
export const toastStore = createStore<Toast[]>([]);
let nextToast = 1;
export function toast(text: string, kind: Toast["kind"] = "info") {
  const id = nextToast++;
  toastStore.set((t) => [...t.filter((x) => x.text !== text), { id, text, kind }]);
  setTimeout(() => toastStore.set((t) => t.filter((x) => x.id !== id)), kind === "error" ? 6000 : 3000);
}
