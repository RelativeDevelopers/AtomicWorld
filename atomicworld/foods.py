"""¿Qué moléculas hay en…? Alimentos de verdad, de las moléculas a los quarks.

Un alimento es una lista de componentes con sus gramos en 100 g: agua, azúcares, etanol, cafeína,
minerales... Cada componente es una molécula del catálogo (data/food_molecules.json) o una fórmula
química cualquiera. Con eso se calcula, para una porción, cuántas moléculas, átomos, protones,
neutrones, electrones y quarks hay.

Lo que no es UNA molécula se cuenta con un modelo, y se dice:
  - proteínas -> aminoácidos medios ("averagina", Senko et al. 1995)
  - almidón y fibra -> unidades de glucosa (C6H10O5)
  - grasas -> un triglicérido típico (trioleína)
  - minerales -> átomos (en el alimento están como iones; los electrones se cuentan como neutros)

Los alimentos de ejemplo (data/foods.json) salen de USDA FoodData Central con tools/build_foods.py,
que guarda la fuente de cada uno. from_fdc() convierte un alimento de FoodData Central (tal como lo
devuelve su API) en componentes, y es lo que usan ese script y la búsqueda.

Como el resto del núcleo, este módulo no imprime nada, no pide datos y no usa la red.
"""
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .chemistry import FormulaError, validate_formula
from .constants import AVOGADRO
from .repository import PeriodicTable

DATA_DIR = Path(__file__).parent / "data"
LANGUAGES = ("es", "ca", "en")

# Límites de lo que se acepta en un alimento propio (y al importar una biblioteca)
MAX_COMPONENTS = 40
MAX_NAME_LENGTH = 80
MAX_FORMULA_LENGTH = 60
MAX_PORTION_GRAMS = 100_000.0
MAX_LIBRARY_FOODS = 200

_UNIT_TO_GRAMS = {"g": 1.0, "mg": 1e-3, "µg": 1e-6, "ug": 1e-6, "mcg": 1e-6}


class FoodError(ValueError):
    """Un alimento no es válido. Lleva un código y sus datos para que cada interfaz lo traduzca."""

    def __init__(self, message: str, code: str, **params):
        super().__init__(message)
        self.code = code
        self.params = params

    def to_dict(self) -> dict:
        return {"code": self.code, "params": self.params}


# --- Catálogo de moléculas -------------------------------------------------------------------

@dataclass(frozen=True)
class FoodMolecule:
    key: str
    formula: str
    kind: str                       # molecule | unit | model | element
    names: dict
    composition: tuple              # ((símbolo, átomos por unidad), ...): admite decimales
    source: str | None = None       # clave de _meta.sources si es un modelo
    fdc_number: int | None = None   # número del nutriente en FoodData Central
    fdc_unit: str | None = None

    def name(self, language: str = "en") -> str:
        return self.names.get(language) or self.names["en"]


_ATOM = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def _decimal_composition(formula: str) -> tuple:
    """'C4.9384H7.7583N1.3577' -> (('C', 4.9384), ('H', 7.7583), ('N', 1.3577)). Sin paréntesis."""
    parts, pos = {}, 0
    while pos < len(formula):
        m = _ATOM.match(formula, pos)
        if not m:
            raise ValueError(f"Bad catalog formula: {formula}")
        parts[m.group(1)] = parts.get(m.group(1), 0.0) + float(m.group(2) or 1)
        pos = m.end()
    return tuple(parts.items())


@lru_cache(maxsize=1)
def _catalog_data() -> dict:
    return json.loads((DATA_DIR / "food_molecules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def molecules() -> dict[str, FoodMolecule]:
    """El catálogo, por clave."""
    out = {}
    for m in _catalog_data()["molecules"]:
        number, unit = (m.get("fdc") or (None, None))
        out[m["key"]] = FoodMolecule(m["key"], m["formula"], m["kind"], m["names"],
                                     _decimal_composition(m["formula"]), m.get("source"), number, unit)
    return out


def model_sources() -> dict[str, str]:
    """Fuente de cada modelo (averagina, unidad de glucosa, trioleína)."""
    return dict(_catalog_data()["_meta"]["sources"])


def custom_molecule(formula: str, table: PeriodicTable) -> FoodMolecule:
    """Una molécula que no está en el catálogo, a partir de su fórmula (H2O, Ca(OH)2...)."""
    formula = formula.strip()
    if len(formula) > MAX_FORMULA_LENGTH:
        raise FoodError("The formula is too long.", "too_long", field="formula", maximum=MAX_FORMULA_LENGTH)
    composition = validate_formula(formula, table)        # FormulaError si no es válida
    return FoodMolecule(f"formula:{formula}", formula, "molecule", {"en": formula},
                        tuple((s, float(n)) for s, n in composition.items()))


# --- Alimentos ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Component:
    molecule: FoodMolecule
    grams_per_100g: float


@dataclass(frozen=True)
class Food:
    id: str
    names: dict                       # {"es": "Manzana", ...}; uno basta en los propios
    components: tuple                 # de Component
    portion_grams: float = 100.0
    portion_names: dict = field(default_factory=dict)   # {"es": "una manzana mediana", ...}
    sources: tuple = ()               # [{"fdc_id": 171688, "description": "...", ...}, ...]
    custom: bool = False              # True si lo ha creado el usuario
    portion_source: str = ""          # de dónde sale el peso de la porción

    def name(self, language: str = "en") -> str:
        return self.names.get(language) or self.names.get("en") or next(iter(self.names.values()), self.id)

    def portion_name(self, language: str = "en") -> str:
        return self.portion_names.get(language) or self.portion_names.get("en", "")

    @property
    def identified_grams_per_100g(self) -> float:
        return sum(c.grams_per_100g for c in self.components)

    @property
    def unidentified_grams_per_100g(self) -> float:
        """Lo que la fuente no desglosa en moléculas (ácidos orgánicos, aromas, sales...)."""
        return max(0.0, 100.0 - self.identified_grams_per_100g)

    def to_dict(self) -> dict:
        """Para guardar en la biblioteca (JSON). Los del catálogo se guardan por su clave."""
        return {
            "id": self.id, "names": dict(self.names), "portion_grams": self.portion_grams,
            "portion_names": dict(self.portion_names), "portion_source": self.portion_source,
            "sources": [dict(s) for s in self.sources],
            "components": [({"formula": c.molecule.formula} if c.molecule.key.startswith("formula:")
                            else {"molecule": c.molecule.key}) | {"grams_per_100g": c.grams_per_100g}
                           for c in self.components],
        }


def _number(value, field_name: str, minimum: float = 0.0, maximum: float = MAX_PORTION_GRAMS,
            strict: bool = False) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise FoodError(f"{field_name} must be a number.", "not_a_number", field=field_name) from None
    if x != x or (x <= minimum if strict else x < minimum):
        raise FoodError(f"{field_name} is too small.", "too_small", field=field_name, minimum=minimum)
    if x > maximum:
        raise FoodError(f"{field_name} is too big.", "too_big", field=field_name, maximum=maximum)
    return x


def food_from_dict(data: dict, table: PeriodicTable | None = None, custom: bool = True) -> Food:
    """Crea (y valida) un alimento a partir de un diccionario: el de la biblioteca, el que manda la
    web o el de data/foods.json. Cada componente es {"molecule": clave} o {"formula": "H2O"}, con
    "grams_per_100g". Si los componentes suman más de 100 g, es un error."""
    if not isinstance(data, dict):
        raise FoodError("A food must be an object.", "invalid_food")
    table = table or PeriodicTable()
    names = {k: str(v).strip() for k, v in (data.get("names") or {}).items()
             if k in LANGUAGES and str(v).strip()}
    if not names:
        raise FoodError("The food needs a name.", "missing_name")
    if any(len(n) > MAX_NAME_LENGTH for n in names.values()):
        raise FoodError("The name is too long.", "too_long", field="name", maximum=MAX_NAME_LENGTH)
    raw = data.get("components") or []
    if not raw:
        raise FoodError("The food has no components.", "no_components")
    if len(raw) > MAX_COMPONENTS:
        raise FoodError("Too many components.", "too_many_components", maximum=MAX_COMPONENTS)

    catalog = molecules()
    components = []
    for item in raw:
        if not isinstance(item, dict):
            raise FoodError("Invalid component.", "invalid_food")
        grams = _number(item.get("grams_per_100g"), "grams_per_100g", 0.0, 100.0, strict=True)
        if item.get("molecule"):
            if item["molecule"] not in catalog:
                raise FoodError(f"Unknown molecule {item['molecule']!r}.", "unknown_molecule",
                                molecule=str(item["molecule"])[:40])
            molecule = catalog[item["molecule"]]
        elif item.get("formula"):
            molecule = custom_molecule(str(item["formula"]), table)
        else:
            raise FoodError("Each component needs a molecule or a formula.", "invalid_food")
        components.append(Component(molecule, grams))
    total = sum(c.grams_per_100g for c in components)
    if total > 100.0 + 1e-6:
        raise FoodError("The components add up to more than 100 g per 100 g.", "over_100",
                        total=round(total, 3))

    portion = _number(data.get("portion_grams", 100.0), "portion_grams", 0.0, MAX_PORTION_GRAMS, strict=True)
    portion_names = {k: str(v).strip()[:MAX_NAME_LENGTH] for k, v in (data.get("portion_names") or {}).items()
                     if k in LANGUAGES and str(v).strip()}
    food_id = str(data.get("id") or "").strip()[:60] or _slug(next(iter(names.values())))
    sources = tuple(dict(s) for s in (data.get("sources") or []) if isinstance(s, dict))
    portion_source = str(data.get("portion_source") or "")[:200]
    return Food(food_id, names, tuple(components), portion, portion_names, sources, custom, portion_source)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "food"


@lru_cache(maxsize=1)
def sample_foods() -> tuple:
    """Los alimentos de ejemplo (data/foods.json). Vacío si todavía no se ha generado."""
    path = DATA_DIR / "foods.json"
    if not path.is_file():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(food_from_dict(d, custom=False) for d in data["foods"])


def find_sample(food_id: str) -> Food:
    for food in sample_foods():
        if food.id == food_id:
            return food
    raise FoodError(f"Unknown food {food_id!r}.", "unknown_food", food=food_id)


# --- Análisis ----------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentAnalysis:
    molecule: FoodMolecule
    grams: float
    units: float          # moléculas (o unidades, o átomos si es un mineral)
    atoms: float
    protons: float
    neutrons: float
    electrons: float

    @property
    def up_quarks(self) -> float:        # protón = uud, neutrón = udd
        return 2 * self.protons + self.neutrons

    @property
    def down_quarks(self) -> float:
        return self.protons + 2 * self.neutrons

    @property
    def quarks(self) -> float:
        return 3 * (self.protons + self.neutrons)


@dataclass(frozen=True)
class FoodAnalysis:
    food: Food
    grams: float
    components: tuple              # de ComponentAnalysis, de más a menos moléculas
    unidentified_grams: float

    def _sum(self, attr: str) -> float:
        return sum(getattr(c, attr) for c in self.components)

    @property
    def molecules(self) -> float:
        return self._sum("units")

    @property
    def atoms(self) -> float:
        return self._sum("atoms")

    @property
    def protons(self) -> float:
        return self._sum("protons")

    @property
    def neutrons(self) -> float:
        return self._sum("neutrons")

    @property
    def electrons(self) -> float:
        return self._sum("electrons")

    @property
    def quarks(self) -> float:
        return self._sum("quarks")

    @property
    def up_quarks(self) -> float:
        return self._sum("up_quarks")

    @property
    def down_quarks(self) -> float:
        return self._sum("down_quarks")


def analyze_food(food: Food, grams: float | None = None, table: PeriodicTable | None = None) -> FoodAnalysis:
    """Moléculas, átomos, protones, neutrones, electrones y quarks de `grams` gramos del alimento
    (por defecto, su porción)."""
    table = table or PeriodicTable()
    grams = food.portion_grams if grams is None else _number(grams, "grams", 0.0, MAX_PORTION_GRAMS, strict=True)
    rows = []
    for c in food.components:
        g = grams * c.grams_per_100g / 100
        molar_mass = sum(table.by_symbol(s).atomic_mass * n for s, n in c.molecule.composition)
        units = g / molar_mass * AVOGADRO
        atoms = protons = neutrons = 0.0
        for symbol, n in c.molecule.composition:
            el = table.by_symbol(symbol)
            atoms += units * n
            protons += units * n * el.protons
            neutrons += units * n * el.avg_neutrons
        rows.append(ComponentAnalysis(c.molecule, g, units, atoms, protons, neutrons, protons))
    rows.sort(key=lambda r: r.units, reverse=True)
    return FoodAnalysis(food, grams, tuple(rows), grams * food.unidentified_grams_per_100g / 100)


# --- FoodData Central ----------------------------------------------------------------------

def fdc_nutrients(fdc_food: dict) -> dict[int, tuple[float, str]]:
    """{número de nutriente: (cantidad en 100 g, unidad)} de un alimento de la API de FoodData
    Central. Acepta las dos formas que devuelve: /food/{id} y /foods/search."""
    out = {}
    for item in fdc_food.get("foodNutrients", []):
        if "nutrient" in item:                     # /food/{id}
            n = item["nutrient"]
            number, unit, amount = n.get("number"), n.get("unitName"), item.get("amount")
        else:                                      # /foods/search
            number, unit, amount = item.get("nutrientNumber"), item.get("unitName"), item.get("value")
        try:
            out[int(float(number))] = (float(amount), str(unit))
        except (TypeError, ValueError):
            continue
    return out


def components_from_fdc(fdc_food: dict) -> list[dict]:
    """Componentes (gramos en 100 g) de un alimento de FoodData Central, con las moléculas del
    catálogo. Si los azúcares no vienen desglosados, no se inventan: quedan como «sin identificar»."""
    nutrients = fdc_nutrients(fdc_food)
    out = []
    for m in molecules().values():
        if m.fdc_number in nutrients:
            amount, unit = nutrients[m.fdc_number]
            factor = _UNIT_TO_GRAMS.get((unit or m.fdc_unit or "g").lower())   # FDC: "G", "MG", "UG"
            if factor is None:
                continue
            grams = amount * factor
            if grams > 0:
                out.append({"molecule": m.key, "grams_per_100g": grams})
    return out


def mix(parts: list[tuple[list[dict], float]]) -> list[dict]:
    """Mezcla de varios alimentos: [(componentes, gramos de ese alimento), ...] -> componentes de la
    mezcla en 100 g. Sirve para recetas como el café con leche (café + leche)."""
    total = sum(g for _c, g in parts)
    grams: dict[str, float] = {}
    for components, g in parts:
        for c in components:
            grams[c["molecule"]] = grams.get(c["molecule"], 0.0) + c["grams_per_100g"] * g / total
    return [{"molecule": k, "grams_per_100g": v} for k, v in grams.items()]
