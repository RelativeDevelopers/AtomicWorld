"""Tu biblioteca de alimentos (los que creas tú), guardada entre sesiones.

Se guarda en ~/.atomicworld/library.json, junto a los ajustes, con el mismo formato que exporta la
web (así un archivo sirve en los dos sitios). Si el archivo no existe o está roto, la biblioteca
empieza vacía; los alimentos que no se pueden leer se saltan, sin impedir arrancar.
"""
import json
from pathlib import Path

from atomicworld import foods

LIBRARY_FILE = Path.home() / ".atomicworld" / "library.json"
FORMAT = "atomicworld-library"


def load(path: Path | None = None) -> list[foods.Food]:
    path = path or LIBRARY_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("foods", []) if isinstance(data, dict) else []
    out = []
    for item in items[:foods.MAX_LIBRARY_FOODS]:
        try:
            out.append(foods.food_from_dict(item))
        except ValueError:              # FoodError y FormulaError
            continue
    return out


def save(library: list[foods.Food], path: Path | None = None) -> bool:
    path = path or LIBRARY_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"format": FORMAT, "version": 1, "foods": [f.to_dict() for f in library]}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
