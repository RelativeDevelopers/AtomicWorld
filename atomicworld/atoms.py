"""Estructura del átomo: configuración electrónica, apantallamiento y tamaño del núcleo.

Lo usa el visor 3D para dibujar las nubes de electrones y el núcleo, pero es Python puro
(sin numpy): cualquier interfaz puede preguntar, por ejemplo, la carga que "siente"
un electrón 4s del hierro.

    shells = subshells(table.find("Fe"))       # (1s², 2s², 2p⁶, 3s², 3p⁶, 3d⁶, 4s²)
    slater_zeff(26, shells, 4, 0)              # 3.75
"""
import re
from dataclasses import dataclass

from .models import Element

ORBITAL_LETTERS = "spdf"
CAPACITY = {0: 2, 1: 6, 2: 10, 3: 14}           # electrones que caben en s, p, d, f

# Configuraciones de los gases nobles, para expandir "[Ar] 3d6 4s2"
NOBLE_GAS_CORES = {
    "He": "1s2",
    "Ne": "[He] 2s2 2p6",
    "Ar": "[Ne] 3s2 3p6",
    "Kr": "[Ar] 3d10 4s2 4p6",
    "Xe": "[Kr] 4d10 5s2 5p6",
    "Rn": "[Xe] 4f14 5d10 6s2 6p6",
}

NUCLEAR_RADIUS_R0_FM = 1.2       # R = r₀ · A^(1/3)

_PART = re.compile(r"([1-7])([spdf])(\d+)")


@dataclass(frozen=True)
class Subshell:
    """Un subnivel ocupado: n = capa (1, 2, 3...), l = forma (0 s, 1 p, 2 d, 3 f)."""
    n: int
    l: int
    electrons: int

    @property
    def label(self) -> str:
        """'3d6' (sin superíndices: la interfaz decide cómo escribirlo)."""
        return f"{self.n}{ORBITAL_LETTERS[self.l]}{self.electrons}"

    @property
    def name(self) -> str:
        """'3d'"""
        return f"{self.n}{ORBITAL_LETTERS[self.l]}"

    @property
    def is_full(self) -> bool:
        return self.electrons == CAPACITY[self.l]


class ConfigError(ValueError):
    pass


def parse_config(text: str) -> tuple[Subshell, ...]:
    """'[Ar] 3d6 4s2' -> todos los subniveles, del más interno al más externo (por n y l)."""
    found: dict[tuple[int, int], int] = {}
    for part in text.split():
        if part.startswith("["):
            core = part.strip("[]")
            if core not in NOBLE_GAS_CORES:
                raise ConfigError(f"Unknown noble gas core: {part}")
            for s in parse_config(NOBLE_GAS_CORES[core]):
                found[(s.n, s.l)] = found.get((s.n, s.l), 0) + s.electrons
            continue
        m = _PART.fullmatch(part)
        if not m:
            raise ConfigError(f"Invalid subshell: {part!r}")
        n, l, e = int(m.group(1)), ORBITAL_LETTERS.index(m.group(2)), int(m.group(3))
        if l >= n:
            raise ConfigError(f"Subshell {part!r} does not exist (l must be < n)")
        found[(n, l)] = found.get((n, l), 0) + e
    shells = tuple(Subshell(n, l, e) for (n, l), e in sorted(found.items()))
    for s in shells:
        if not 0 < s.electrons <= CAPACITY[s.l]:
            raise ConfigError(f"Subshell {s.name} cannot hold {s.electrons} electrons")
    return shells


def subshells(element: Element) -> tuple[Subshell, ...]:
    return parse_config(element.electron_config)


def full_config(element: Element) -> str:
    """Configuración sin abreviar: '1s2 2s2 2p6 3s2 3p6 3d6 4s2'."""
    return " ".join(s.label for s in subshells(element))


def valence_shell(element: Element) -> int:
    """La capa más externa ocupada (el periodo del elemento)."""
    return max(s.n for s in subshells(element))


# --- Reglas de Slater (1930) ---------------------------------------------------------
#
# Cada electrón "siente" la carga del núcleo menos la de los electrones que lo apantallan:
#     Z_ef = Z − S
# Los subniveles se agrupan así, de dentro a fuera:
#     [1s] [2s 2p] [3s 3p] [3d] [4s 4p] [4d] [4f] [5s 5p] [5d] [5f] [6s 6p] [6d] [7s 7p]
# - Electrones del mismo grupo: 0,35 cada uno (0,30 en el 1s).
# - Para un electrón s o p: los de capa n − 1 apantallan 0,85; los de n − 2 o menos, 1,00.
# - Para un electrón d o f: todos los de grupos interiores apantallan 1,00.
# - Los de grupos exteriores no apantallan.

def slater_group(n: int, l: int) -> tuple[int, int]:
    """Orden de los grupos de Slater: s y p juntos; d y f, cada uno en su grupo."""
    return n, 0 if l <= 1 else l - 1


def slater_screening(shells, n: int, l: int) -> float:
    own = slater_group(n, l)
    s = 0.0
    for sh in shells:
        group = slater_group(sh.n, sh.l)
        if group == own:
            others = sh.electrons - (1 if (sh.n, sh.l) == (n, l) else 0)
            s += others * (0.30 if n == 1 else 0.35)
        elif group < own:
            if l >= 2:
                s += sh.electrons * 1.00
            elif sh.n == n - 1:
                s += sh.electrons * 0.85
            elif sh.n < n - 1:
                s += sh.electrons * 1.00
            # (un grupo interior con la misma n, p. ej. ninguno para s/p: no se da)
    return s


def slater_zeff(z: int, shells, n: int, l: int) -> float:
    """Carga nuclear efectiva que siente un electrón del subnivel (n, l)."""
    if not any((s.n, s.l) == (n, l) for s in shells):
        raise ValueError(f"Subshell {n}{ORBITAL_LETTERS[l]} is empty")
    return z - slater_screening(shells, n, l)


# --- Núcleo ----------------------------------------------------------------------

def nuclear_radius_fm(mass_number: int) -> float:
    """Radio del núcleo, R ≈ 1,2 fm · A^(1/3): todos los núcleos tienen casi la misma densidad."""
    if mass_number < 1:
        raise ValueError("Mass number must be ≥ 1")
    return NUCLEAR_RADIUS_R0_FM * mass_number ** (1 / 3)


def atom_to_nucleus_ratio(element: Element, mass_number: int | None = None) -> float:
    """Cuántas veces es mayor el átomo (radio de van der Waals) que su núcleo."""
    a = mass_number or element.mass_number
    return element.vdw_radius_pm * 1000 / nuclear_radius_fm(a)
