"""Textos de la consola y del visor 3D en cada idioma (ui/locales/*.json).

El núcleo (atomicworld) nunca redacta frases: devuelve datos y códigos. Esta capa los
convierte en texto. Los nombres de elementos y partículas vienen del núcleo (atomicworld.names).

    tr = Translator("es")
    tr.t("viewer.hud.level", n=1, name="...")
    tr.count(26, "proton")          # "26 protones"
    tr.num(3.75)                    # "3,75"
"""
import json
from functools import lru_cache
from pathlib import Path

from atomicworld import names

LOCALES_DIR = Path(__file__).parent / "locales"
LANGUAGES = names.LANGUAGES               # ("en", "es", "ca")


@lru_cache(maxsize=None)
def _load(lang: str) -> dict:
    return json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def language_names() -> dict[str, str]:
    """{"en": "English", "es": "Español", "ca": "Català"}"""
    return {lang: _load(lang)["_meta"]["name"] for lang in LANGUAGES}


class Translator:
    def __init__(self, lang: str = names.DEFAULT_LANGUAGE):
        self.set_language(lang)

    def set_language(self, lang: str) -> None:
        if lang not in LANGUAGES:
            raise ValueError(f"Unknown language: {lang!r}")
        self.lang = lang
        self.texts = _load(lang)
        self.dec = self.texts["_meta"]["decimal_separator"]
        self.thousands = self.texts["_meta"]["thousands_separator"]

    def next_language(self) -> str:
        """Pasa al siguiente idioma (tecla L del visor) y lo devuelve."""
        self.set_language(LANGUAGES[(LANGUAGES.index(self.lang) + 1) % len(LANGUAGES)])
        return self.lang

    # --- textos -----------------------------------------------------------------
    def _lookup(self, key: str):
        node = self.texts
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def t(self, key: str, **params) -> str:
        """Texto de la clave, con {parámetros}. Si falta, devuelve la clave (se ve el fallo)."""
        value = self._lookup(key)
        if not isinstance(value, str):
            return key
        return value.format(**params) if params else value

    def lines(self, key: str, **params) -> list[str]:
        """Para las claves que son una lista de líneas (explicaciones del HUD)."""
        value = self._lookup(key)
        if not isinstance(value, list):
            return [key]
        return [line.format(**params) if params else line for line in value]

    def count(self, n: int, noun: str) -> str:
        """'1 protón', '26 protones' (las formas están en units.<noun>.one / other)."""
        form = "one" if n == 1 else "other"
        return self.t(f"units.{noun}.{form}", n=self.int(n))

    # --- números ------------------------------------------------------------------
    def num(self, value: float, digits: int = 2) -> str:
        text = f"{value:,.{digits}f}"
        return text.replace(",", "\0").replace(".", self.dec).replace("\0", self.thousands)

    def int(self, value: int) -> str:
        return f"{int(round(value)):,d}".replace(",", self.thousands)

    def sci(self, value: float, digits: int = 1) -> str:
        """1.2e-10 -> '1,2×10⁻¹⁰'"""
        if value == 0:
            return "0"
        mantissa, exponent = f"{value:.{digits}e}".split("e")
        sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
        return mantissa.replace(".", self.dec) + "×10" + str(int(exponent)).translate(sup)

    # --- nombres (vienen del núcleo) ----------------------------------------------
    def element(self, number: int) -> str:
        return names.element(number, self.lang)

    def of(self, name: str) -> str:
        """'de hierro' en castellano; 'de ferro' o 'd'or' en catalán (apóstrofo); en inglés, igual.

        En castellano y catalán los nombres de los elementos van en minúscula dentro de la frase.
        """
        if self.lang == "es":
            return f"de {name.lower()}"
        if self.lang == "ca":
            name = name.lower()
            return f"d'{name}" if _catalan_elides(name) else f"de {name}"
        return name

    def particle(self, name: str) -> str:
        return names.particle(name, self.lang)


_VOWELS = "aeiouàèéíïòóúü"


def _catalan_elides(word: str) -> bool:
    """En catalán 'de' se apostrofa ante vocal o h + vocal (d'Or, d'Hidrogen), salvo ante
    i/u seguidas de vocal, que suenan como consonante (de Iode)."""
    w = word.lower()
    if w.startswith("h"):
        w = w[1:]
    if not w or w[0] not in _VOWELS:
        return False
    return not (w[0] in "iu" and len(w) > 1 and w[1] in _VOWELS)
