"""Modelos de datos: cómo es un elemento y cómo es una partícula.

Usar dataclasses en lugar de diccionarios hace que una errata como
el['Atomic mas (u)'] no pase desapercibida: el.atomic_mas da error al momento
y el editor te lo marca.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Element:
    number: int
    name: str
    symbol: str
    atomic_mass: float          # en unidades de masa atómica (u) = g/mol
    protons: int
    neutrons: int               # del isótopo más abundante (o del más estable si no hay naturales)
    avg_neutrons: float         # media ponderada por abundancia isotópica: la de una muestra real
    aliases: tuple[str, ...] = ()   # otras grafías aceptadas en la búsqueda ('Aluminum', 'Cesium')
    density_g_cm3: float | None = None
    melting_c: float | None = None
    boiling_c: float | None = None
    electron_config: str = ""   # estado fundamental, abreviado: "[Ar] 3d6 4s2"
    vdw_radius_pm: float | None = None  # radio de van der Waals: el "tamaño" del átomo
    vdw_estimated: bool = False         # True si no se ha medido (superpesados: se usa el homólogo)
    color: str | None = None            # color convencional de Jmol, en hexadecimal (no es real)

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(**{**d, "aliases": tuple(d.get("aliases") or ())})

    @property
    def mass_number(self) -> int:
        return self.protons + self.neutrons

    @property
    def electrons(self) -> int:
        """Electrones del átomo neutro."""
        return self.protons


@dataclass(frozen=True)
class Particle:
    name: str
    family: str                 # Quark, Antiquark, Lepton, Antilepton, Gauge Boson, Scalar Boson, Hypothetical
    mass_mev: float             # siempre en MeV/c²
    charge: Fraction            # en unidades de la carga del electrón
    spin: Fraction
    binary: str                 # código de 8 bits para el Big Bang
    mass_is_upper_limit: bool = False   # True si solo se conoce una cota superior (neutrinos)
    hypothetical: bool = False          # True si no se ha observado (gravitón)

    @classmethod
    def from_dict(cls, d: dict) -> "Particle":
        return cls(
            name=d["name"],
            family=d["family"],
            mass_mev=d["mass_mev"],
            charge=Fraction(d["charge"]),
            spin=Fraction(d["spin"]),
            binary=d["binary"],
            mass_is_upper_limit=d.get("mass_is_upper_limit", False),
            hypothetical=d.get("hypothetical", False),
        )


@dataclass(frozen=True)
class DecayMode:
    mode: str                   # código de NUBASE: B- (β⁻), B+ (β⁺), EC, A (α), SF (fisión), p, n...
    intensity: float | None     # % de las desintegraciones; None si no se conoce bien


@dataclass(frozen=True)
class Isotope:
    """Un isótopo: Z protones y A − Z neutrones (C-14: z=6, a=14)."""
    z: int
    a: int
    mass_u: float
    abundance: float | None     # % en la naturaleza; None si no hay de forma natural
    status: str                 # "stable", "radioactive" o "unknown" (no ligado o sin medir)
    half_life_s: float | None   # semivida en segundos; None si es estable o no se conoce
    decay: tuple[DecayMode, ...] = ()
    spin: str | None = None
    parity: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Isotope":
        return cls(**{**d, "decay": tuple(DecayMode(**m) for m in d.get("decay") or ())})

    @property
    def neutrons(self) -> int:
        return self.a - self.z

    @property
    def is_natural(self) -> bool:
        return bool(self.abundance)

    @property
    def is_stable(self) -> bool:
        return self.status == "stable"

    @property
    def main_decay(self) -> DecayMode | None:
        return self.decay[0] if self.decay else None
