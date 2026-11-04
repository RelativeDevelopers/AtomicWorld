"""Nombres de elementos, partículas y familias en cada idioma.

Son DATOS (como la masa o el símbolo), no textos de una interfaz: por eso viven en el núcleo
y los usan la web, la consola y el visor 3D. Los textos de cada interfaz (menús, botones,
HUD) siguen en la propia interfaz.

    names.element(26, "es")        -> "Hierro"
    names.particle("Up", "ca")     -> "Up"
    names.family("Quark", "es")    -> "Quarks"
"""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

NAMES_DIR = Path(__file__).parent / "data" / "names"
LANGUAGES = ("en", "es", "ca")
DEFAULT_LANGUAGE = "en"


@lru_cache(maxsize=None)
def table(lang: str) -> dict:
    """Todo el archivo de nombres de un idioma: {"elements", "particles", "families"}."""
    if lang not in LANGUAGES:
        raise ValueError(f"Unknown language: {lang!r}")
    return json.loads((NAMES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def element(number: int, lang: str) -> str:
    return table(lang)["elements"][str(number)]


def particle(name: str, lang: str) -> str:
    """Nombre traducido a partir del nombre interno (en inglés) de la partícula."""
    return table(lang)["particles"].get(name, name)


def family(name: str, lang: str) -> str:
    return table(lang)["families"].get(name, name)


def normalize(text: str) -> str:
    """Para buscar: minúsculas, sin acentos ni espacios sobrantes ('  Fósforo ' -> 'fosforo').

    La ñ y la ç también se simplifican (n, c), así que 'Estano' encuentra el Estaño.
    """
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
