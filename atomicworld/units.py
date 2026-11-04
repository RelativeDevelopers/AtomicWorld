"""Conversor de masas: de eV/c² a kilogramos y viceversa.

Viene del programa StandardModelConversor.py (ver legacy/). En física de partículas las
masas se dan en unidades de energía (E = mc² → m = E/c²): el electrón "pesa" 0.511 MeV/c².
Para pasarlas a kilogramos:

    1. eV → julios:   E [J] = E [eV] · e        (e = carga del electrón, 1.602176634·10⁻¹⁹ C)
    2. julios → kg:   m [kg] = E [J] / c²       (c = 299 792 458 m/s)

Desde 2019 el SI define e y c con valores EXACTOS, así que el factor eV/c² → kg también es
exacto: 1 eV/c² = 1.602176634·10⁻¹⁹ / 299 792 458² kg ≈ 1.78266192·10⁻³⁶ kg.

Además de eV/c² y kg, el conversor usa la unidad de masa atómica (u, o dalton), que es la
de la tabla periódica: así se puede comparar un quark con un átomo.

Como el resto del núcleo, este módulo no imprime nada: devuelve datos.
"""
import math
from dataclasses import dataclass

from .constants import PROTON_MASS_MEV
from .models import Particle

# --- Constantes (SI 2019 y CODATA 2022) ------------------------------------------
ELEMENTARY_CHARGE_C = 1.602176634e-19      # exacta: julios por electronvoltio
SPEED_OF_LIGHT_M_S = 299_792_458           # exacta
EV_IN_KG = ELEMENTARY_CHARGE_C / SPEED_OF_LIGHT_M_S ** 2   # 1 eV/c² en kg ≈ 1.78266192e-36
ATOMIC_MASS_UNIT_MEV = 931.49410372        # 1 u en MeV/c² (CODATA 2022)
ELECTRON_MASS_MEV = 0.51099895069          # CODATA 2022

# Cuántos MeV/c² vale 1 unidad de cada tipo. El orden es el de los menús.
UNITS_IN_MEV: dict[str, float] = {
    "eV": 1e-6,
    "keV": 1e-3,
    "MeV": 1.0,
    "GeV": 1e3,
    "TeV": 1e6,
    "u": ATOMIC_MASS_UNIT_MEV,
    "g": 1e-3 / (EV_IN_KG * 1e6),          # 1 g en MeV/c²
    "kg": 1 / (EV_IN_KG * 1e6),            # 1 kg en MeV/c² ≈ 5.61e29
}
ENERGY_UNITS = ("eV", "keV", "MeV", "GeV", "TeV")


class UnitError(ValueError):
    """Unidad desconocida. Lleva un código para que la web la traduzca."""

    def __init__(self, unit: str):
        super().__init__(f"Unknown mass unit: {unit!r}. Use one of: {', '.join(UNITS_IN_MEV)}")
        self.code = "unknown_unit"
        self.params = {"unit": unit}


def symbol(unit: str) -> str:
    """'MeV' -> 'MeV/c²'; 'kg' -> 'kg'."""
    return f"{unit}/c²" if unit in ENERGY_UNITS else unit


def _factor(unit: str) -> float:
    try:
        return UNITS_IN_MEV[unit]
    except KeyError:
        raise UnitError(unit) from None


def to_mev(value: float, unit: str) -> float:
    return value * _factor(unit)


def from_mev(mev: float, unit: str) -> float:
    return mev / _factor(unit)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """convert(0.511, 'MeV', 'kg') -> 9.109e-31"""
    return from_mev(to_mev(value, from_unit), to_unit)


def mev_to_kg(mev: float) -> float:
    """La función del programa original: MeV/c² → eV → julios → kg."""
    joules = mev * 1e6 * ELEMENTARY_CHARGE_C
    return joules / SPEED_OF_LIGHT_M_S ** 2


def best_energy_unit(mev: float) -> str:
    """La unidad de energía en la que la masa se lee mejor (entre 1 y 1000)."""
    for unit in reversed(ENERGY_UNITS):
        if mev >= UNITS_IN_MEV[unit]:
            return unit
    return "eV"


@dataclass(frozen=True)
class Mass:
    """Una masa, guardada en MeV/c², que se puede pedir en cualquier unidad."""
    mev: float

    def __post_init__(self):
        if not math.isfinite(self.mev) or self.mev < 0:
            raise ValueError("A mass must be a finite number ≥ 0.")

    @classmethod
    def of(cls, value: float, unit: str) -> "Mass":
        return cls(to_mev(value, unit))

    def to(self, unit: str) -> float:
        return from_mev(self.mev, unit)

    @property
    def kg(self) -> float:
        return mev_to_kg(self.mev)

    @property
    def electron_masses(self) -> float:
        return self.mev / ELECTRON_MASS_MEV

    @property
    def proton_masses(self) -> float:
        return self.mev / PROTON_MASS_MEV

    def all_units(self) -> dict[str, float]:
        return {unit: self.to(unit) for unit in UNITS_IN_MEV}


@dataclass(frozen=True)
class ParticleMass:
    particle: Particle
    mass: Mass

    @property
    def is_massless(self) -> bool:
        return self.mass.mev == 0


def particle_masses(particles) -> list[ParticleMass]:
    """Lo que hacía StandardModelConversor.py: la masa de cada partícula, en todas las unidades."""
    return [ParticleMass(p, Mass(p.mass_mev)) for p in particles]


def closest_particle(mass: Mass, particles) -> tuple[Particle, float] | None:
    """La partícula de masa más parecida (por cociente, no por diferencia) y cuántas veces
    más pesada es `mass` que ella. Se ignoran las partículas sin masa, las hipotéticas y las
    que solo tienen una cota superior (los neutrinos), porque su masa no se conoce."""
    if mass.mev == 0:
        return None
    candidates = [p for p in particles
                  if p.mass_mev > 0 and not p.hypothetical and not p.mass_is_upper_limit]
    if not candidates:
        return None
    best = min(candidates, key=lambda p: abs(math.log(mass.mev / p.mass_mev)))
    return best, mass.mev / best.mass_mev
