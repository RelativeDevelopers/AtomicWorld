"""
Genera atomicworld/data/foods.json (los alimentos de ejemplo de «¿Qué moléculas hay en…?») con
datos de USDA FoodData Central (https://fdc.nal.usda.gov/), base SR Legacy.

Uso (desde la carpeta raíz del proyecto, con internet):
    python tools/build_foods.py                     # usa la clave de prueba DEMO_KEY
    python tools/build_foods.py --key TU_CLAVE      # o la variable de entorno FDC_API_KEY

La clave es gratuita (https://fdc.nal.usda.gov/api-key-signup). No se guarda en ningún archivo.
DEMO_KEY basta para este script (hace ~12 peticiones), pero tiene un límite de unas 30 por hora.

Para cada alimento: busca su descripción exacta en SR Legacy, descarga sus nutrientes y su
porción, y los convierte en moléculas con atomicworld.foods.components_from_fdc(). Las mezclas
(café con leche) se calculan con atomicworld.foods.mix(). En foods.json queda la fuente de todo:
el número FDC, la descripción y de dónde sale el peso de la porción.

Solo usa la biblioteca estándar de Python.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from atomicworld import foods  # noqa: E402

API = "https://api.nal.usda.gov/fdc/v1"
FL_OZ_ML = 29.5735
CUP_ML = 236.588

# (descripción en SR Legacy, texto que debe contener si hay varias que empiezan igual)
BEER = ("Alcoholic beverage, beer, regular, all", None)
COFFEE = ("Beverages, coffee, brewed, prepared with tap water", None)
MILK = ("Milk, whole, 3.25% milkfat", "with added vitamin D")
APPLE = ("Apples, raw, with skin", None)
PICKLE = ("Pickles, cucumber, dill or kosher dill", None)
CARROT = ("Carrots, raw", None)

# Cada alimento: sus partes [(alimento FDC, ml o gramos)] y su porción:
#   {"ml": 330}          -> volumen, con la densidad que da FDC (sus porciones en fl oz o cup)
#   {"fdc": "medium"}    -> la porción de FDC cuya descripción contiene esa palabra
FOODS = [
    {"id": "beer", "parts": [(BEER, 1)], "portion": {"ml": 330},
     "names": {"es": "Cerveza", "ca": "Cervesa", "en": "Beer"},
     "portion_names": {"es": "un tercio (330 ml)", "ca": "un terç (330 ml)", "en": "a bottle (330 ml)"}},
    {"id": "coffee_with_milk", "parts": [(COFFEE, 100), (MILK, 100)], "parts_in": "ml", "portion": {"ml": 200},
     "names": {"es": "Café con leche", "ca": "Cafè amb llet", "en": "White coffee"},
     "portion_names": {"es": "una taza (100 ml de café y 100 ml de leche)",
                       "ca": "una tassa (100 ml de cafè i 100 ml de llet)",
                       "en": "a cup (100 ml of coffee and 100 ml of milk)"}},
    {"id": "milk", "parts": [(MILK, 1)], "portion": {"ml": 250},
     "names": {"es": "Leche entera", "ca": "Llet sencera", "en": "Whole milk"},
     "portion_names": {"es": "un vaso (250 ml)", "ca": "un got (250 ml)", "en": "a glass (250 ml)"}},
    {"id": "apple", "parts": [(APPLE, 1)], "portion": {"fdc": "medium"},
     "names": {"es": "Manzana", "ca": "Poma", "en": "Apple"},
     "portion_names": {"es": "una manzana mediana", "ca": "una poma mitjana", "en": "a medium apple"}},
    {"id": "pickle", "parts": [(PICKLE, 1)], "portion": {"fdc": "medium"},
     "names": {"es": "Pepinillo en vinagre", "ca": "Cogombret en vinagre", "en": "Dill pickle"},
     "portion_names": {"es": "un pepinillo mediano", "ca": "un cogombret mitjà", "en": "a medium pickle"}},
    {"id": "carrot", "parts": [(CARROT, 1)], "portion": {"fdc": "medium"},
     "names": {"es": "Zanahoria", "ca": "Pastanaga", "en": "Carrot"},
     "portion_names": {"es": "una zanahoria mediana", "ca": "una pastanaga mitjana", "en": "a medium carrot"}},
]


def get(path: str, key: str, **params) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode({**params, 'api_key': key})}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 429:
            sys.exit("FoodData Central: demasiadas peticiones con DEMO_KEY. Espera una hora o usa tu clave (--key).")
        if error.code == 403:
            sys.exit("FoodData Central rechaza la clave. Revisa --key o FDC_API_KEY.")
        raise


_cache: dict = {}


def fdc_food(spec: tuple, key: str) -> dict:
    """Busca la descripción en SR Legacy y descarga el alimento completo."""
    if spec in _cache:
        return _cache[spec]
    prefix, prefer = spec
    found = get("/foods/search", key, query=prefix, dataType="SR Legacy", pageSize=50)["foods"]
    matches = [f for f in found if f["description"].lower().startswith(prefix.lower())]
    if prefer:
        matches = [f for f in matches if prefer.lower() in f["description"].lower()] or matches
    exact = [f for f in matches if f["description"].lower() == prefix.lower()]
    matches = exact or matches
    if len(matches) != 1:
        options = "\n  ".join(f"{f['fdcId']}: {f['description']}" for f in (matches or found[:10]))
        sys.exit(f"No encuentro una sola coincidencia para «{prefix}». Opciones:\n  {options}")
    food = get(f"/food/{matches[0]['fdcId']}", key)
    _cache[spec] = food
    return food


def density_g_per_ml(food: dict) -> tuple[float, str]:
    """Densidad a partir de las porciones de FDC (fl oz o cup). Sin porciones de volumen: 1 g/ml."""
    for p in food.get("foodPortions", []):
        text = f"{p.get('modifier', '')} {p.get('portionDescription', '')} {p.get('measureUnit', {}).get('name', '')}".lower()
        amount = float(p.get("amount") or 1)
        if "fl oz" in text:
            return p["gramWeight"] / (amount * FL_OZ_ML), f"{amount:g} fl oz = {p['gramWeight']:g} g"
        if "cup" in text:
            return p["gramWeight"] / (amount * CUP_ML), f"{amount:g} cup = {p['gramWeight']:g} g"
    return 1.0, "sin porción de volumen en FDC: se toma 1 g/ml"


def portion_by_name(food: dict, word: str) -> tuple[float, str]:
    for p in food.get("foodPortions", []):
        text = f"{p.get('amount', 1):g} {p.get('modifier', '')} {p.get('portionDescription', '')}".strip()
        if word in text.lower():
            return float(p["gramWeight"]), f"{text} = {p['gramWeight']:g} g"
    options = "; ".join(f"{p.get('modifier', '')} {p.get('portionDescription', '')}" for p in food.get("foodPortions", []))
    sys.exit(f"«{food['description']}» no tiene una porción «{word}». Tiene: {options}")


def build(key: str) -> dict:
    out = []
    for spec in FOODS:
        parts, sources = [], []
        total_grams = 0.0
        for part_spec, amount in spec["parts"]:
            food = fdc_food(part_spec, key)
            density, density_note = density_g_per_ml(food)
            grams = amount * density if spec.get("parts_in") == "ml" else amount
            parts.append((foods.components_from_fdc(food), grams))
            total_grams += grams
            source = {"fdc_id": food["fdcId"], "description": food["description"],
                      "data_type": food.get("dataType", "SR Legacy")}
            if spec.get("parts_in") == "ml":
                source["amount"] = f"{amount:g} ml = {grams:.1f} g ({density_note})"
            sources.append(source)

        components = parts[0][0] if len(parts) == 1 else foods.mix(parts)
        if "ml" in spec["portion"]:
            if spec.get("parts_in") == "ml":           # mezcla: la porción es la suma de las partes
                grams, note = total_grams * spec["portion"]["ml"] / sum(a for _s, a in spec["parts"]), "suma de las partes"
            else:
                density, note = density_g_per_ml(fdc_food(spec["parts"][0][0], key))
                grams = spec["portion"]["ml"] * density
        else:
            grams, note = portion_by_name(fdc_food(spec["parts"][0][0], key), spec["portion"]["fdc"])

        entry = {
            "id": spec["id"], "names": spec["names"], "portion_grams": round(grams, 1),
            "portion_names": spec["portion_names"], "portion_source": note, "sources": sources,
            "components": [{"molecule": c["molecule"], "grams_per_100g": float(f"{c['grams_per_100g']:.6g}")}
                           for c in components],
        }
        foods.food_from_dict(entry, custom=False)          # valida: moléculas conocidas, ≤ 100 g...
        out.append(entry)
        identified = sum(c["grams_per_100g"] for c in entry["components"])
        print(f"  {spec['names']['es']:<22} {entry['portion_grams']:>7.1f} g   "
              f"{len(entry['components']):>2} componentes   {identified:5.1f} g de cada 100 g identificados")
        for s in sources:
            print(f"      FDC {s['fdc_id']}: {s['description']}")
    return {
        "_meta": {
            "source": "USDA, Agricultural Research Service. FoodData Central, SR Legacy (2018). "
                      "https://fdc.nal.usda.gov/ — dominio público (CC0).",
            "generated": datetime.date.today().isoformat(),
            "how": "python tools/build_foods.py: gramos de cada nutriente en 100 g, convertidos en las "
                   "moléculas de food_molecules.json.",
        },
        "foods": out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", default=os.environ.get("FDC_API_KEY", "DEMO_KEY"),
                        help="clave de la API de FoodData Central (por defecto DEMO_KEY)")
    args = parser.parse_args()
    print("Descargando de FoodData Central...")
    data = build(args.key)
    path = ROOT / "atomicworld" / "data" / "foods.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nGuardado: {path.relative_to(ROOT)} ({len(data['foods'])} alimentos)")


if __name__ == "__main__":
    main()
