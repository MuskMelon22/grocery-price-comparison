import pytest

from app.services.matcher import MIN_SCORE, Item, match, score
from app.services.normalizer import extract_brand, parse_pack


def item(id_: int, name: str) -> Item:
    qty, kind = parse_pack(name)
    return Item(id_, name, extract_brand(name), kind, qty)


# 10 sample pairs: (BigBasket name, JioMart name, should they match?)
PAIRS = [
    ("Amul Taaza Toned Milk 1 L Pouch", "Amul Taaza Homogenised Toned Milk 1 L", True),
    ("Amul Gold Full Cream Milk 500 ml", "Amul Gold Homogenised Standardised Milk 500 ml", True),
    ("Aashirvaad Shudh Chakki Atta 5 kg", "Aashirvaad Whole Wheat Atta 5 kg", True),
    ("Fortune Sunlite Refined Sunflower Oil 1 L", "Fortune Sun Lite Sunflower Refined Oil 1 L (Pouch)", True),
    ("Tata Salt Iodised 1 kg", "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", True),
    ("Amul Butter - Pasteurised 500 g", "Amul Pasteurised Butter 500 g (Carton)", True),
    ("Amul Taaza Toned Milk 1 L", "Amul Taaza Toned Milk 500 ml", False),  # different pack size
    ("Amul Butter 500 g", "Mother Dairy Butter 500 g", False),  # different brand
    ("Nestle Milkmaid Condensed Milk 380 g", "Nestle Everyday Dairy Whitener 380 g", False),  # different product
    ("Amul Masti Dahi 400 g", "Amul Fresh Paneer 400 g", False),  # different product
]


@pytest.mark.parametrize("bb, jm, expected", PAIRS)
def test_pairs(bb, jm, expected):
    assert bool(match([item(1, bb)], [item(2, jm)])) is expected, score(bb, jm)


def test_greedy_is_one_to_one_and_best_first():
    bb = [item(1, "Amul Taaza Toned Milk 1 L"), item(2, "Amul Gold Full Cream Milk 1 L")]
    jm = [item(10, "Amul Gold Homogenised Full Cream Milk 1 L"), item(11, "Amul Taaza Homogenised Toned Milk 1 L")]
    pairs = {(a, b) for a, b, _ in match(bb, jm)}
    assert pairs == {(1, 11), (2, 10)}


def test_score_range():
    assert score("Amul Butter 500 g", "Amul Butter 500 g") == 1.0
    assert score("", "Amul") == 0.0
    assert MIN_SCORE == 0.55
