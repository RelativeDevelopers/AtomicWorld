"""Búsqueda en FoodData Central (atomicworld/fdc.py), sin internet: _request se sustituye por
respuestas de PRUEBA con la forma real de la API."""
import io
import urllib.error

import pytest

from atomicworld import fdc, foods

SEARCH = {"foods": [
    {"fdcId": 171688, "description": "Apples, raw, with skin", "dataType": "SR Legacy", "foodCategory": "Fruits"},
    {"fdcId": 1750339, "description": "Apples, fuji, with skin, raw", "dataType": "Foundation"},
]}
DETAIL = {
    "fdcId": 171688, "description": "Apples, raw, with skin", "dataType": "SR Legacy",
    "foodNutrients": [
        {"nutrient": {"number": "255", "unitName": "g"}, "amount": 85.6},
        {"nutrient": {"number": "212", "unitName": "g"}, "amount": 5.9},
        {"nutrient": {"number": "306", "unitName": "mg"}, "amount": 107.0},
    ],
    "foodPortions": [{"amount": 1, "modifier": "medium (3\" dia)", "gramWeight": 182.0,
                      "measureUnit": {"name": "undetermined"}}],
}


@pytest.fixture
def fake(monkeypatch):
    calls = []

    def request(path, body=None):
        calls.append((path, body))
        return SEARCH if path == "/foods/search" else DETAIL
    monkeypatch.setattr(fdc, "_request", request)
    return calls


def test_search(fake):
    results = fdc.search("  apple   raw ")
    assert results[0] == {"fdc_id": 171688, "description": "Apples, raw, with skin",
                          "data_type": "SR Legacy", "category": "Fruits"}
    path, body = fake[0]
    assert body["query"] == "apple raw" and body["dataType"] == ["Foundation", "SR Legacy"]


def test_empty_search_does_not_call_the_api(fake):
    assert fdc.search("   ") == [] and fake == []


def test_food_with_its_portion_and_source(fake):
    food = fdc.food(171688)
    assert food.id == "fdc-171688" and food.name("es") == "Apples, raw, with skin"
    assert food.portion_grams == 182.0 and food.portion_name("en") == '1 medium (3" dia)'
    assert food.sources[0]["fdc_id"] == 171688
    grams = {c.molecule.key: c.grams_per_100g for c in food.components}
    assert grams == pytest.approx({"water": 85.6, "fructose": 5.9, "potassium": 0.107})
    assert foods.analyze_food(food).molecules > 0


def test_rounding_over_100_g_is_scaled(monkeypatch):
    detail = {**DETAIL, "foodNutrients": [{"nutrient": {"number": "255", "unitName": "g"}, "amount": 99.0},
                                          {"nutrient": {"number": "212", "unitName": "g"}, "amount": 1.5}]}
    monkeypatch.setattr(fdc, "_request", lambda path, body=None: detail)
    assert fdc.food(1).identified_grams_per_100g == pytest.approx(100.0)


def test_food_without_composition(monkeypatch):
    monkeypatch.setattr(fdc, "_request", lambda path, body=None: {"fdcId": 5, "description": "x", "foodNutrients": []})
    with pytest.raises(fdc.FdcError) as error:
        fdc.food(5)
    assert error.value.code == "no_composition"


def test_portion_without_portions():
    assert fdc.portion({}) == (100.0, "100 g")
    assert fdc.portion({"foodPortions": [{"amount": 1, "measureUnit": {"name": "cup"}, "gramWeight": 240}]}) == (240.0, "1 cup")


@pytest.mark.parametrize("status, code", [(429, "rate_limited"), (403, "bad_key"), (404, "not_found"), (500, "network")])
def test_http_errors_become_codes(monkeypatch, status, code):
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError("url", status, "x", {}, io.BytesIO(b""))
    monkeypatch.setattr(fdc.urllib.request, "urlopen", fail)
    with pytest.raises(fdc.FdcError) as error:
        fdc.search("apple")
    assert error.value.code == code


def test_no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.URLError("offline")
    monkeypatch.setattr(fdc.urllib.request, "urlopen", fail)
    with pytest.raises(fdc.FdcError) as error:
        fdc.food(1)
    assert error.value.code == "network"


def test_the_key_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("FDC_API_KEY", raising=False)
    assert fdc.api_key() == "DEMO_KEY"
    monkeypatch.setenv("FDC_API_KEY", " abc ")
    assert fdc.api_key() == "abc"
