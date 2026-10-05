"""Pair the same product across BigBasket and JioMart."""
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.normalizer import normalize_name

MIN_SCORE = 0.55
QTY_TOLERANCE = 0.02  # pack sizes within 2% count as equal


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    brand: str | None
    pack_kind: str
    pack_qty_base: float | None


def score(a: str, b: str) -> float:
    """Average of character similarity and word overlap on normalised names (0..1)."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return round((seq + overlap) / 2, 3)


def _compatible(a: Item, b: Item) -> bool:
    if a.pack_kind == "unknown" or a.pack_kind != b.pack_kind or not a.pack_qty_base or not b.pack_qty_base:
        return False
    if abs(a.pack_qty_base - b.pack_qty_base) > QTY_TOLERANCE * max(a.pack_qty_base, b.pack_qty_base):
        return False
    return not (a.brand and b.brand and a.brand != b.brand)


def match(bigbasket: list[Item], jiomart: list[Item]) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching, best score first. Returns (bigbasket_id, jiomart_id, score)."""
    # ponytail: O(n*m) pair scan; fine for ~50 items per store per search
    candidates = sorted(
        ((score(a.name, b.name), a.id, b.id) for a in bigbasket for b in jiomart if _compatible(a, b)),
        reverse=True,
    )
    used_a, used_b, pairs = set(), set(), []
    for s, a_id, b_id in candidates:
        if s < MIN_SCORE:
            break
        if a_id in used_a or b_id in used_b:
            continue
        used_a.add(a_id)
        used_b.add(b_id)
        pairs.append((a_id, b_id, s))
    return pairs
