"""Carga de datos desde los JSON y búsquedas.

Sustituye a los diccionarios `indexelements` / `indexsubelements` del original:
ya no hay que mantener índices a mano, se busca directamente por nombre o símbolo.
"""
import json
from pathlib import Path

from . import names
from .models import Element, Isotope, Particle

DATA_DIR = Path(__file__).parent / "data"


class PeriodicTable:
    def __init__(self, path: Path = DATA_DIR / "elements.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.elements: list[Element] = sorted(
            (Element.from_dict(e) for e in raw), key=lambda e: e.number
        )
        self._by_key: dict[str, Element] = {}
        for el in self.elements:
            keys = [el.name, el.symbol, str(el.number), *el.aliases]
            keys += [names.element(el.number, lang) for lang in names.LANGUAGES]
            for key in keys:
                self._add_key(names.normalize(key), el)

    def _add_key(self, key: str, el: Element) -> None:
        other = self._by_key.setdefault(key, el)
        if other is not el:          # dos elementos con el mismo nombre en idiomas distintos
            raise ValueError(f"Ambiguous search key {key!r}: {other.symbol} and {el.symbol}")

    def find(self, text: str) -> Element:
        """Busca por nombre en cualquier idioma ('Oxygen', 'Oxígeno', 'Oxigen'), símbolo ('O')
        o número atómico ('8'), sin importar mayúsculas ni acentos."""
        try:
            return self._by_key[names.normalize(text)]
        except KeyError:
            raise ValueError(f"Unknown element: {text!r}") from None

    def by_symbol(self, symbol: str) -> Element:
        """Búsqueda estricta por símbolo, respetando mayúsculas ('Co' ≠ 'CO')."""
        for el in self.elements:
            if el.symbol == symbol:
                return el
        raise ValueError(f"Unknown element symbol: {symbol!r}")

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)


class ParticleCatalog:
    def __init__(self, path: Path = DATA_DIR / "particles.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.particles: list[Particle] = [Particle.from_dict(p) for p in raw]
        self._by_name: dict[str, Particle] = {}
        for p in self.particles:
            for key in [p.name] + [names.particle(p.name, lang) for lang in names.LANGUAGES]:
                self._by_name.setdefault(names.normalize(key), p)
        self._by_binary = {p.binary: p for p in self.particles}

    def find(self, name: str) -> Particle:
        """Por nombre en cualquier idioma ('Electron', 'Electrón', 'Electró')."""
        try:
            return self._by_name[names.normalize(name)]
        except KeyError:
            raise ValueError(f"Unknown particle: {name!r}") from None

    def by_binary(self, byte: str) -> Particle | None:
        """Devuelve la partícula cuyo código coincide con el byte, o None."""
        return self._by_binary.get(byte)

    def __iter__(self):
        return iter(self.particles)

    def __len__(self):
        return len(self.particles)


class IsotopeTable:
    """Los ~3.500 isótopos conocidos (NUBASE). Se carga aparte de la tabla periódica
    porque pesa más y solo lo necesita quien elige un isótopo concreto."""

    def __init__(self, path: Path = DATA_DIR / "isotopes.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.isotopes: list[Isotope] = [Isotope.from_dict(i) for i in raw]
        self._by_za = {(i.z, i.a): i for i in self.isotopes}
        self._by_z: dict[int, list[Isotope]] = {}
        for i in self.isotopes:
            self._by_z.setdefault(i.z, []).append(i)

    def of(self, z: int) -> list[Isotope]:
        """Todos los isótopos de un elemento, de menor a mayor número másico."""
        return self._by_z.get(z, [])

    def natural(self, z: int) -> list[Isotope]:
        """Los que hay en la naturaleza, del más abundante al menos."""
        return sorted((i for i in self.of(z) if i.is_natural), key=lambda i: -i.abundance)

    def get(self, z: int, a: int) -> Isotope:
        try:
            return self._by_za[(z, a)]
        except KeyError:
            raise ValueError(f"Unknown isotope: Z={z}, A={a}") from None

    def default(self, element: Element) -> Isotope:
        """El isótopo que usa la tabla periódica (el más abundante, o el más estable)."""
        return self.get(element.number, element.mass_number)

    def __iter__(self):
        return iter(self.isotopes)

    def __len__(self):
        return len(self.isotopes)
