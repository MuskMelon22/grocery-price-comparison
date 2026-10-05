"""Turn raw product names into comparable data: pack size, unit price, brand, category."""
import re

# unit -> (kind, multiplier to base unit: grams / millilitres / items)
UNITS = {
    "g": ("weight", 1), "gm": ("weight", 1), "gms": ("weight", 1), "gram": ("weight", 1),
    "grams": ("weight", 1), "kg": ("weight", 1000), "kgs": ("weight", 1000),
    "ml": ("volume", 1), "l": ("volume", 1000), "ltr": ("volume", 1000), "ltrs": ("volume", 1000),
    "litre": ("volume", 1000), "liter": ("volume", 1000), "litres": ("volume", 1000),
    "pc": ("count", 1), "pcs": ("count", 1), "pieces": ("count", 1), "nos": ("count", 1),
}
_UNIT = "|".join(sorted(UNITS, key=len, reverse=True))  # longest first so "kgs" beats "kg"
MULTI_RE = re.compile(rf"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*({_UNIT})\b", re.I)  # 2 x 500 g
MULTI_REV_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*({_UNIT})\s*[x×*]\s*(\d+)\b", re.I)  # 400ml X 3
QTY_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*({_UNIT})\b", re.I)  # 500 g
PACK_OF_RE = re.compile(r"pack\s*of\s*(\d+)", re.I)  # Pack of 3

KNOWN_BRANDS = [
    "mother dairy", "tata sampann", "tata tea", "saffola", "amul", "aashirvaad", "tata", "fortune",
    "britannia", "nestle", "maggi", "parle", "sunfeast", "gowardhan", "govind", "nandini", "heritage",
    "akshayakalpa", "milky mist", "india gate", "daawat", "kohinoor", "madhur", "catch", "everest",
    "mdh", "patanjali", "dhara", "gemini", "freedom", "red label", "brooke bond", "taj mahal",
    "bru", "nescafe", "haldiram's", "haldirams", "lays", "kurkure", "good life", "fresho",
    "bb royal", "reliance", "jio", "epigamia", "chitale", "warana", "gokul", "prabhat", "dabur",
    "kissan", "del monte", "real", "tropicana", "paper boat", "harvest gold", "modern", "english oven",
]
STOPWORDS = {"fresh", "pack", "of", "pouch", "the", "and", "with", "a", "in", "for", "combo", "pouches"}

CATEGORIES = {  # keyword in query -> category (plan section 10)
    "dairy": ["milk", "butter", "curd", "paneer", "cheese", "ghee", "dahi", "yogurt", "cream", "lassi"],
    "staples": ["atta", "rice", "dal", "flour", "sugar", "salt", "maida", "besan", "rava", "poha", "wheat"],
    "oils": ["oil"],
    "beverages": ["tea", "coffee", "juice", "drink", "cola"],
    "snacks": ["biscuit", "chips", "namkeen", "maggi", "noodles", "cookies", "chocolate"],
    "bakery": ["bread", "bun", "cake", "rusk"],
    "eggs & meat": ["egg", "chicken", "mutton", "fish"],
    "spices": ["masala", "turmeric", "chilli", "haldi", "jeera", "spice"],
}


def parse_pack(name: str) -> tuple[float | None, str]:
    """Pack size in base units and its kind, e.g. "Amul Butter 2 x 500 g" -> (1000.0, "weight")."""
    m = MULTI_RE.search(name)
    if m:
        kind, mult = UNITS[m.group(3).lower()]
        return int(m.group(1)) * float(m.group(2)) * mult, kind
    m = MULTI_REV_RE.search(name)
    if m:
        kind, mult = UNITS[m.group(2).lower()]
        return float(m.group(1)) * int(m.group(3)) * mult, kind
    m = QTY_RE.search(name)
    packs = PACK_OF_RE.search(name)
    n = int(packs.group(1)) if packs else 1
    if m:
        kind, mult = UNITS[m.group(2).lower()]
        return n * float(m.group(1)) * mult, kind
    if packs:
        return float(n), "count"
    return None, "unknown"


def unit_price(price: float, qty_base: float | None, kind: str) -> float | None:
    """₹ per 100 g / 100 ml, or ₹ per item for counted packs."""
    if not qty_base or kind == "unknown":
        return None
    per = 1 if kind == "count" else 100
    return round(price / qty_base * per, 2)


def extract_brand(name: str) -> str:
    low = name.lower()
    for brand in KNOWN_BRANDS:
        if low.startswith(brand + " ") or low == brand:
            return brand
    first = re.split(r"\s+", low.strip(), maxsplit=1)[0]
    return re.sub(r"[^\w']", "", first)


def normalize_name(name: str) -> str:
    """Lowercase, drop punctuation, pack-size tokens and filler words: used only for matching."""
    s = MULTI_REV_RE.sub(" ", MULTI_RE.sub(" ", name.lower()))
    s = QTY_RE.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(w for w in s.split() if w not in STOPWORDS and not w.isdigit())


def category_for(query: str) -> str:
    q = query.lower()
    for cat, words in CATEGORIES.items():
        if any(w in q for w in words):
            return cat
    return "other"


def discount_pct(price: float, mrp: float) -> float:
    return round((mrp - price) / mrp * 100, 1) if mrp > price > 0 else 0.0
