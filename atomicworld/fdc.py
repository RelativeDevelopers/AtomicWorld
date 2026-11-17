"""Búsqueda en USDA FoodData Central (https://fdc.nal.usda.gov/), para «¿Qué moléculas hay en…?».

Busca en las dos bases más completas, Foundation y SR Legacy (los nombres están en inglés), y
convierte el alimento elegido en un alimento de atomicworld.foods, con su fuente y su porción.

La clave de la API se lee de la variable de entorno FDC_API_KEY (gratuita:
https://fdc.nal.usda.gov/api-key-signup). Sin ella se usa DEMO_KEY, que tiene un límite de unas
30 peticiones por hora. La clave NUNCA va en el código ni en un repositorio.

Solo usa la biblioteca estándar. No imprime nada: los errores son FdcError con un código
(rate_limited, bad_key, network, not_found) que cada interfaz traduce.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from . import foods

API = "https://api.nal.usda.gov/fdc/v1"
DATA_TYPES = ("Foundation", "SR Legacy")
MAX_QUERY_LENGTH = 80
MAX_RESULTS = 15
TIMEOUT_S = 20


class FdcError(RuntimeError):
    def __init__(self, message: str, code: str, **params):
        super().__init__(message)
        self.code = code
        self.params = params

    def to_dict(self) -> dict:
        return {"code": self.code, "params": self.params}


def api_key() -> str:
    return os.environ.get("FDC_API_KEY", "").strip() or "DEMO_KEY"


def _request(path: str, body: dict | None = None) -> dict:
    """Una llamada a la API. Separada para que los tests la sustituyan."""
    url = f"{API}{path}?{urllib.parse.urlencode({'api_key': api_key()})}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                              "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise FdcError("Too many requests to FoodData Central.", "rate_limited") from None
        if error.code in (401, 403):
            raise FdcError("FoodData Central rejected the API key.", "bad_key") from None
        if error.code == 404:
            raise FdcError("Food not found in FoodData Central.", "not_found") from None
        raise FdcError(f"FoodData Central answered {error.code}.", "network", status=error.code) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise FdcError("Cannot reach FoodData Central.", "network") from None


def search(query: str, limit: int = 10) -> list[dict]:
    """[{fdc_id, description, data_type, category}] de los alimentos que coinciden."""
    query = " ".join(str(query).split())[:MAX_QUERY_LENGTH]
    if not query:
        return []
    data = _request("/foods/search", {"query": query, "dataType": list(DATA_TYPES),
                                      "pageSize": max(1, min(int(limit), MAX_RESULTS))})
    return [{"fdc_id": int(f["fdcId"]), "description": str(f.get("description", "")),
             "data_type": str(f.get("dataType", "")),
             "category": str(f.get("foodCategory") or "")} for f in data.get("foods", [])]


def portion(detail: dict) -> tuple[float, str]:
    """La primera porción con peso que da FDC, y cómo se llama: (182.0, '1 medium (3" dia)').
    Sin porciones: 100 g."""
    for p in detail.get("foodPortions", []):
        grams = p.get("gramWeight")
        if not grams:
            continue
        unit = (p.get("measureUnit") or {}).get("name", "")
        words = [w for w in (p.get("portionDescription"), unit if unit != "undetermined" else "", p.get("modifier")) if w]
        text = " ".join(dict.fromkeys(str(w).strip() for w in words))   # sin repetir palabras iguales
        amount = p.get("amount") or 1
        return float(grams), f"{amount:g} {text}".strip() if text else f"{float(grams):g} g"
    return 100.0, "100 g"


def food(fdc_id: int) -> foods.Food:
    """El alimento completo de FoodData Central, ya convertido en moléculas."""
    detail = _request(f"/food/{int(fdc_id)}")
    grams, portion_name = portion(detail)
    data = {
        "id": f"fdc-{int(detail.get('fdcId', fdc_id))}",
        "names": {"en": str(detail.get("description", f"FDC {fdc_id}"))[:foods.MAX_NAME_LENGTH]},
        "portion_grams": grams,
        "portion_names": {"en": portion_name[:foods.MAX_NAME_LENGTH]},
        "portion_source": f"FoodData Central: {portion_name} = {grams:g} g",
        "sources": [{"fdc_id": int(detail.get("fdcId", fdc_id)), "description": str(detail.get("description", "")),
                     "data_type": str(detail.get("dataType", ""))}],
        "components": foods.components_from_fdc(detail),
    }
    if not data["components"]:
        raise FdcError("FoodData Central has no composition for this food.", "no_composition", fdc_id=int(fdc_id))
    # Algunas fichas de FDC suman unas décimas más de 100 g (redondeos): se ajusta a 100 g.
    total = sum(c["grams_per_100g"] for c in data["components"])
    if total > 100:
        for c in data["components"]:
            c["grams_per_100g"] *= 100 / total
    return foods.food_from_dict(data, custom=False)
