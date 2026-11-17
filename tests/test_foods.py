"""Tests de «¿Qué moléculas hay en…?» (atomicworld/foods.py y tools/build_foods.py).

Las respuestas de FoodData Central de aquí abajo son de PRUEBA (números redondos), con la forma
exacta de su API: sirven para comprobar las cuentas sin internet. Los datos reales están en
data/foods.json, generado con tools/build_foods.py.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from atomicworld import foods
from atomicworld.chemistry import FormulaError
from atomicworld.constants import AVOGADRO

ROOT = Path(__file__).resolve().parents[1]


def water(grams_per_100g=100.0, portion=18.015):
    return foods.food_from_dict({"names": {"es": "Agua"}, "portion_grams": portion,
                                 "components": [{"molecule": "water", "grams_per_100g": grams_per_100g}]})


# --- Catálogo -------------------------------------------------------------------------

def test_catalog_has_names_in_three_languages():
    for m in foods.molecules().values():
        assert set(m.names) == {"es", "ca", "en"}, m.key
        assert m.kind in {"molecule", "unit", "model", "element"}


def test_models_say_where_they_come_from():
    sources = foods.model_sources()
    for m in foods.molecules().values():
        if m.kind in {"unit", "model"}:
            assert m.source in sources, m.key


def test_fdc_numbers_are_unique():
    numbers = [m.fdc_number for m in foods.molecules().values()]
    assert len(numbers) == len(set(numbers))


def test_averagine_mass():
    # El aminoácido medio pesa 111,1254 Da (Senko et al. 1995)
    one = foods.food_from_dict({"names": {"en": "x"}, "portion_grams": 111.1254,
                                "components": [{"molecule": "protein", "grams_per_100g": 100}]})
    assert foods.analyze_food(one).molecules == pytest.approx(AVOGADRO, rel=1e-3)


# --- Cuentas -----------------------------------------------------------------------------

def test_one_mole_of_water():
    a = foods.analyze_food(water())
    assert a.molecules == pytest.approx(AVOGADRO, rel=1e-4)
    assert a.atoms == pytest.approx(3 * AVOGADRO, rel=1e-4)
    assert a.protons == pytest.approx(10 * AVOGADRO, rel=1e-4)
    assert a.electrons == a.protons                        # átomos neutros
    assert a.quarks == pytest.approx(3 * (a.protons + a.neutrons))
    assert a.up_quarks + a.down_quarks == pytest.approx(a.quarks)


def test_grams_scale_linearly():
    f = water(portion=100)
    assert foods.analyze_food(f, 200).molecules == pytest.approx(2 * foods.analyze_food(f, 100).molecules)


def test_unidentified_part():
    f = water(grams_per_100g=90, portion=50)
    assert f.unidentified_grams_per_100g == pytest.approx(10)
    assert foods.analyze_food(f).unidentified_grams == pytest.approx(5)


def test_components_sorted_by_number_of_molecules():
    f = foods.food_from_dict({"names": {"en": "x"}, "components": [
        {"molecule": "sucrose", "grams_per_100g": 10}, {"molecule": "water", "grams_per_100g": 10}]})
    keys = [c.molecule.key for c in foods.analyze_food(f).components]
    assert keys == ["water", "sucrose"]


def test_custom_formula():
    f = foods.food_from_dict({"names": {"es": "Salmuera"}, "components": [
        {"molecule": "water", "grams_per_100g": 90}, {"formula": "NaCl", "grams_per_100g": 10}]})
    salt = next(c for c in foods.analyze_food(f, 58.44).components if c.molecule.formula == "NaCl")
    assert salt.units == pytest.approx(0.1 * AVOGADRO, rel=1e-3)


# --- Validación (alimentos propios y bibliotecas importadas) -----------------------------

@pytest.mark.parametrize("data, code", [
    ({"components": [{"molecule": "water", "grams_per_100g": 10}]}, "missing_name"),
    ({"names": {"es": "x"}, "components": []}, "no_components"),
    ({"names": {"es": "x"}, "components": [{"molecule": "kryptonite", "grams_per_100g": 1}]}, "unknown_molecule"),
    ({"names": {"es": "x"}, "components": [{"molecule": "water", "grams_per_100g": 60},
                                           {"molecule": "sucrose", "grams_per_100g": 60}]}, "over_100"),
    ({"names": {"es": "x"}, "components": [{"molecule": "water", "grams_per_100g": 0}]}, "too_small"),
    ({"names": {"es": "x"}, "components": [{"molecule": "water", "grams_per_100g": "mucho"}]}, "not_a_number"),
    ({"names": {"es": "x" * 200}, "components": [{"molecule": "water", "grams_per_100g": 1}]}, "too_long"),
    ({"names": {"es": "x"}, "portion_grams": -1, "components": [{"molecule": "water", "grams_per_100g": 1}]}, "too_small"),
])
def test_invalid_foods(data, code):
    with pytest.raises(foods.FoodError) as error:
        foods.food_from_dict(data)
    assert error.value.code == code


def test_invalid_formula_is_a_formula_error():
    with pytest.raises(FormulaError):
        foods.food_from_dict({"names": {"es": "x"}, "components": [{"formula": "Xx2", "grams_per_100g": 1}]})


def test_round_trip_for_the_library():
    f = foods.food_from_dict({"names": {"es": "Salmuera", "en": "Brine"}, "portion_grams": 250,
                              "portion_names": {"es": "un vaso"}, "components": [
                                  {"molecule": "water", "grams_per_100g": 90}, {"formula": "NaCl", "grams_per_100g": 10}]})
    again = foods.food_from_dict(json.loads(json.dumps(f.to_dict())))
    assert again == f


# --- FoodData Central (respuestas de prueba con la forma real de la API) ----------------

FDC_DETAIL = {   # /food/{fdcId}
    "fdcId": 1, "description": "Test food", "dataType": "SR Legacy",
    "foodNutrients": [
        {"nutrient": {"number": "255", "name": "Water", "unitName": "g"}, "amount": 80.0},
        {"nutrient": {"number": "212", "name": "Fructose", "unitName": "g"}, "amount": 5.0},
        {"nutrient": {"number": "262", "name": "Caffeine", "unitName": "mg"}, "amount": 40.0},
        {"nutrient": {"number": "321", "name": "Carotene, beta", "unitName": "UG"}, "amount": 500.0},
        {"nutrient": {"number": "205", "name": "Carbohydrate, by difference", "unitName": "g"}, "amount": 15.0},
    ],
    "foodPortions": [{"amount": 1, "modifier": "medium (3\" dia)", "gramWeight": 182.0},
                     {"amount": 1, "modifier": "fl oz", "gramWeight": 30.0}],
}
FDC_SEARCH_ITEM = {   # un elemento de /foods/search
    "fdcId": 2, "description": "Test food 2",
    "foodNutrients": [{"nutrientNumber": "255", "nutrientName": "Water", "unitName": "G", "value": 90.0},
                      {"nutrientNumber": "221", "nutrientName": "Alcohol, ethyl", "unitName": "G", "value": 4.0}],
}


def test_components_from_fdc_detail():
    grams = {c["molecule"]: c["grams_per_100g"] for c in foods.components_from_fdc(FDC_DETAIL)}
    assert grams == pytest.approx({"water": 80.0, "fructose": 5.0, "caffeine": 0.040, "beta_carotene": 0.0005})


def test_components_from_fdc_search():
    grams = {c["molecule"]: c["grams_per_100g"] for c in foods.components_from_fdc(FDC_SEARCH_ITEM)}
    assert grams == {"water": 90.0, "ethanol": 4.0}


def test_mix():
    coffee = [{"molecule": "water", "grams_per_100g": 99.0}, {"molecule": "caffeine", "grams_per_100g": 0.04}]
    milk = [{"molecule": "water", "grams_per_100g": 88.0}, {"molecule": "lactose", "grams_per_100g": 5.0}]
    grams = {c["molecule"]: c["grams_per_100g"] for c in foods.mix([(coffee, 100), (milk, 100)])}
    assert grams == pytest.approx({"water": 93.5, "caffeine": 0.02, "lactose": 2.5})


def _build_foods_module():
    spec = importlib.util.spec_from_file_location("build_foods", ROOT / "tools" / "build_foods.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_script_portions():
    build = _build_foods_module()
    assert build.portion_by_name(FDC_DETAIL, "medium")[0] == 182.0
    density, _note = build.density_g_per_ml(FDC_DETAIL)
    assert density == pytest.approx(30.0 / 29.5735)


def test_a_cup_of_8_fl_oz_is_a_cup():
    # FDC escribe «cup (8 fl oz)»: es una taza (236,6 ml), no una onza
    build = _build_foods_module()
    coffee = {"foodPortions": [{"amount": 1, "modifier": "cup (8 fl oz)", "gramWeight": 237.0}]}
    assert build.density_g_per_ml(coffee)[0] == pytest.approx(237.0 / 236.588)
    both = {"foodPortions": [{"amount": 1, "modifier": "cup (8 fl oz)", "gramWeight": 237.0},
                             {"amount": 1, "modifier": "fl oz", "gramWeight": 29.6}]}
    assert build.density_g_per_ml(both)[0] == pytest.approx(29.6 / 29.5735)


def test_build_script_runs_with_a_fake_api(monkeypatch):
    build = _build_foods_module()
    portions = [{"amount": 1, "modifier": "medium", "gramWeight": 100.0},
                {"amount": 1, "modifier": "large (4\" long)", "gramWeight": 135.0},
                {"amount": 1, "modifier": "fl oz", "gramWeight": 29.5735}]

    def fake_get(path, key, **params):
        if path == "/foods/search":
            return {"foods": [{"fdcId": 7, "description": params["query"]}]}
        return {**FDC_DETAIL, "fdcId": 7, "description": "x", "foodPortions": portions}

    monkeypatch.setattr(build, "get", fake_get)
    data = build.build("TEST")
    assert len(data["foods"]) == len(build.FOODS)
    beer = next(f for f in data["foods"] if f["id"] == "beer")
    assert beer["portion_grams"] == pytest.approx(330.0)
    for entry in data["foods"]:
        foods.food_from_dict(entry, custom=False)


# --- Los alimentos de ejemplo (cuando ya se han generado) --------------------------------

SAMPLES = foods.sample_foods()


@pytest.mark.skipif(not SAMPLES, reason="data/foods.json todavía no se ha generado (tools/build_foods.py)")
def test_sample_foods_are_sensible():
    by_id = {f.id: f for f in SAMPLES}
    for f in SAMPLES:
        assert set(f.names) == {"es", "ca", "en"} and f.sources
        assert 60 <= f.identified_grams_per_100g <= 100.0
    water_share = {k: next(c.grams_per_100g for c in f.components if c.molecule.key == "water")
                   for k, f in by_id.items()}
    assert all(70 < w < 100 for w in water_share.values())        # casi todo es agua
    if "beer" in by_id:
        assert any(c.molecule.key == "ethanol" for c in by_id["beer"].components)
    if "coffee_with_milk" in by_id:
        keys = {c.molecule.key for c in by_id["coffee_with_milk"].components}
        assert {"caffeine", "lactose"} <= keys
