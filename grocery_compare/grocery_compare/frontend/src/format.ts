import type { PackKind, StoreKey, StoreName } from "./types";

export const STORE_NAME: Record<StoreKey, StoreName> = { bigbasket: "BigBasket", jiomart: "JioMart" };
export const STORE_COLOR: Record<StoreName, string> = { BigBasket: "#84c225", JioMart: "#0078ad" };

export const rupee = (n: number | null | undefined, digits = 0) =>
  n == null ? "–" : "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: 2 });

export function packLabel(qty: number | null, kind: PackKind): string {
  if (qty == null || kind === "unknown") return "";
  if (kind === "count") return `${qty} pc${qty === 1 ? "" : "s"}`;
  const [small, big] = kind === "weight" ? ["g", "kg"] : ["ml", "L"];
  return qty >= 1000 ? `${+(qty / 1000).toFixed(2)} ${big}` : `${+qty.toFixed(1)} ${small}`;
}

export const unitSuffix = (kind: PackKind) =>
  kind === "weight" ? "/100 g" : kind === "volume" ? "/100 ml" : kind === "count" ? "/item" : "";

/** Backend datetimes are naive UTC. */
export const asDate = (s: string) => new Date(/Z|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z");
export const when = (s: string | null | undefined) =>
  s ? asDate(s).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "never";
