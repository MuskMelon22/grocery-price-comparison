// Mirrors backend/app/schemas.py. Datetimes are naive UTC ISO strings.
export type StoreKey = "bigbasket" | "jiomart";
export type StoreName = "BigBasket" | "JioMart";
export type PackKind = "weight" | "volume" | "count" | "unknown";

export interface Product {
  id: number;
  store: StoreName;
  name: string;
  brand: string | null;
  image_url: string | null;
  url: string;
  pack_qty_base: number | null;
  pack_kind: PackKind;
  category: string | null;
  price: number;
  mrp: number;
  discount_pct: number;
  unit_price: number | null;
  in_stock: boolean;
  scraped_at: string;
}

export interface MatchRow {
  match_id: number;
  match_score: number;
  bigbasket: Product;
  jiomart: Product;
  cheaper: StoreKey | null;
  saving_abs: number;
  saving_pct: number;
}

export interface SearchResponse {
  query: string;
  pincode: string;
  scraped_at: string | null;
  warnings: string[];
  matched: MatchRow[];
  only_bigbasket: Product[];
  only_jiomart: Product[];
}

export interface ScrapeJob {
  run_id: string;
  query: string;
  pincode: string;
  status: "running" | "done" | "error";
  messages: string[];
  cached: boolean;
}

export interface HistoryPoint {
  store: StoreName;
  product_id: number;
  price: number;
  mrp: number;
  discount_pct: number;
  unit_price: number | null;
  in_stock: boolean;
  pincode: string;
  scraped_at: string;
}

export interface HistoryResponse {
  product: Product;
  counterpart: Product | null;
  match_score: number | null;
  history: HistoryPoint[];
  stats: { store: StoreName; lowest: number; highest: number; average: number; current: number }[];
}

export interface BasketItemIn {
  match_id?: number;
  product_ids?: number[];
  qty: number;
}

export interface BasketResponse {
  lines: { name: string; qty: number; bigbasket: number | null; jiomart: number | null; best_store: StoreKey | null }[];
  totals: Record<StoreKey, number>;
  missing: Record<StoreKey, number>;
  best_split: Record<StoreKey, string[]>;
  best_split_total: number;
  saving_vs_best_single: number | null;
  saving_vs_worst_single: number | null;
}

type PerStore<T> = Record<StoreName, T>;
export interface Summary {
  products_tracked: number;
  snapshots: number;
  matched_pairs: number;
  last_scrape: Partial<PerStore<string | null>>;
  win_rate: PerStore<number>;
  ties_pct: number;
  avg_price_diff_pct: number | null;
  median_price_diff_pct: number | null;
  avg_discount: PerStore<number | null>;
  category_comparison: ({ category: string } & PerStore<number | null>)[];
  top_gaps: { name: string; bigbasket: number; jiomart: number; gap: number; cheaper: string; product_id: number }[];
  volatility: PerStore<number | null>;
  trend: { day: string; store: StoreName; unit_price: number }[];
}
