import pytest

from app.services.normalizer import (
    category_for, discount_pct, extract_brand, normalize_name, parse_pack, unit_price,
)


@pytest.mark.parametrize("name, expected", [
    ("Amul Taaza Homogenised Toned Milk 1 L", (1000, "volume")),
    ("Amul Butter 500 g", (500, "weight")),
    ("Aashirvaad Shudh Chakki Atta 5 kg", (5000, "weight")),
    ("Fortune Sunflower Oil 1.5 L", (1500, "volume")),
    ("Amul Taaza Toned Milk 250 ml", (250, "volume")),
    ("Amul Butter 2 x 500 g", (1000, "weight")),
    ("Oatey Oat Milk 1.6L (8 x 200ml)", (1600, "volume")),
    ("Govind Flavoured Milk 200 Ml (Pack Of 12)", (2400, "volume")),
    ("Fresho Farm Eggs Pack of 6", (6, "count")),
    ("Blue Dragon Light Coconut Milk 1200ml (Pack of 3) (400ml X 3)", (1200, "volume")),
    ("OATEY Oat Milk-Chocolate, Sugar Free, 200ml* 8", (1600, "volume")),
    ("Aptamil Gold Stage 2 - 1.2 kgs", (1200, "weight")),
    ("Tata Tea Gold 500gm", (500, "weight")),
    ("Farm Fresh Brown Eggs", (None, "unknown")),
])
def test_parse_pack(name, expected):
    assert parse_pack(name) == expected


def test_unit_price():
    assert unit_price(76, 1000, "volume") == 7.6  # ₹ per 100 ml
    assert unit_price(60, 6, "count") == 10  # ₹ per egg
    assert unit_price(60, None, "unknown") is None


def test_brand():
    assert extract_brand("Mother Dairy Toned Milk 500 ml") == "mother dairy"
    assert extract_brand("Amul Gold Milk 1 L") == "amul"
    assert extract_brand("Heritage Toned Milk") == "heritage"
    assert extract_brand("Zingo, Crunchy Chips 50 g") == "zingo"  # unknown brand -> first word


def test_normalize_name_drops_sizes_and_fillers():
    assert normalize_name("Amul Taaza Toned Milk, 1 L (Pouch)") == "amul taaza toned milk"


def test_category_and_discount():
    assert category_for("amul butter 500g") == "dairy"
    assert category_for("sunflower oil") == "oils"
    assert category_for("dog food") == "other"
    assert discount_pct(75, 100) == 25.0
    assert discount_pct(100, 100) == 0.0
