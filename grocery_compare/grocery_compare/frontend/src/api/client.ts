import type { BasketItemIn, BasketResponse, HistoryResponse, ScrapeJob, SearchResponse, StoreName, Summary } from "../types";

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "") + "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_URL + path, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new Error("Can't reach the backend. Is it running on port 8000?");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail
        : Array.isArray(detail) ? detail.map((d: { msg: string }) => d.msg).join("; ")
        : `Request failed (${res.status})`,
    );
  }
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string | number | boolean>) =>
  new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();

export const api = {
  startScrape: (query: string, pincode: string, force = false) =>
    request<ScrapeJob>("/scrape", { method: "POST", body: JSON.stringify({ query, pincode, force }) }),
  scrapeStatus: (runId: string) => request<ScrapeJob>(`/scrape/${runId}`),
  // cached=true: never starts a scrape (POST /scrape already did)
  search: (q: string, pincode: string) => request<SearchResponse>(`/search?${qs({ q, pincode, cached: true })}`),
  history: (id: number, days: number) => request<HistoryResponse>(`/products/${id}/history?days=${days}`),
  basket: (items: BasketItemIn[], pincode: string) =>
    request<BasketResponse>("/basket/compare", { method: "POST", body: JSON.stringify({ items, pincode }) }),
  summary: () => request<Summary>("/analytics/summary"),
  discounts: () => request<Record<StoreName, number[]>>("/analytics/discounts"),
  csvUrl: (q: string, pincode: string) => `${API_URL}/export/csv?${qs({ q, pincode })}`,
};
