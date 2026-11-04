"""Cálculos químicos: de gramos a moles, moléculas, átomos, nucleones y quarks.

Sustituye a los cuatro bloques casi idénticos del original (1, 2, 3 y 4 elementos):
ahora un solo bucle sirve para cualquier número de elementos.
"""
import re
from dataclasses import dataclass

from .constants import (AVOGADRO, NEUTRON_MASS_MEV, PROTON_MASS_MEV,
                        QUARKS_PER_NEUTRON, QUARKS_PER_PROTON)
from .models import Element
from .repository import ParticleCatalog, PeriodicTable


class FormulaError(ValueError):
    """La fórmula química no es válida.

    Además del mensaje (en inglés, para la consola), lleva un código y sus datos,
    para que otra interfaz (la web) pueda escribir el error en su idioma:
        FormulaError("Empty parentheses.", "empty_parentheses")
        FormulaError("...", "unknown_symbols", symbols=["Xx"])
    """

    def __init__(self, message: str, code: str = "invalid_formula", **params):
        super().__init__(message)
        self.code = code
        self.params = params

    def to_dict(self) -> dict:
        return {"code": self.code, "params": self.params}


# Un token es: símbolo (Mayúscula + minúscula opcional), paréntesis, o número.
_TOKEN = re.compile(r"([A-Z][a-z]?)|(\()|(\))|(\d+)|(\s+)")


def parse_formula(formula: str) -> dict[str, int]:
    """Convierte una fórmula en {símbolo: cantidad}.

    'H2O'      -> {'H': 2, 'O': 1}
    'Ca(OH)2'  -> {'Ca': 1, 'O': 2, 'H': 2}
    'CH3COOH'  -> {'C': 2, 'H': 4, 'O': 2}   (los repetidos se suman)
    """
    if not formula or not formula.strip():
        raise FormulaError("The formula is empty.", "empty_formula")

    stack: list[dict[str, int]] = [{}]
    pos = 0
    last_group: dict[str, int] | None = None   # lo último añadido, por si viene un número

    while pos < len(formula):
        match = _TOKEN.match(formula, pos)
        if not match:
            raise FormulaError(f"Unexpected character {formula[pos]!r} at position {pos + 1}.",
                               "unexpected_character", char=formula[pos], position=pos + 1)
        symbol, open_p, close_p, number, _space = match.groups()
        pos = match.end()

        if symbol:
            last_group = {symbol: 1}
            _merge(stack[-1], last_group)
        elif open_p:
            stack.append({})
            last_group = None
        elif close_p:
            if len(stack) == 1:
                raise FormulaError("Closing parenthesis without an opening one.", "unmatched_closing")
            group = stack.pop()
            if not group:
                raise FormulaError("Empty parentheses.", "empty_parentheses")
            last_group = group
            _merge(stack[-1], group)
        elif number:
            if last_group is None:
                raise FormulaError(f"Number {number} has nothing before it to multiply.",
                                   "nothing_to_multiply", number=number)
            n = int(number)
            if n == 0:
                raise FormulaError("A subscript cannot be 0.", "zero_subscript")
            # Ya se sumó una vez; añadimos las (n - 1) copias restantes.
            _merge(stack[-1], {s: c * (n - 1) for s, c in last_group.items()})
            last_group = None

    if len(stack) != 1:
        raise FormulaError("Unclosed parenthesis.", "unclosed_parenthesis")
    return stack[0]


def _merge(target: dict[str, int], source: dict[str, int]) -> None:
    for s, c in source.items():
        target[s] = target.get(s, 0) + c


@dataclass(frozen=True)
class ElementBreakdown:
    """Lo que aporta UN elemento a la muestra."""
    element: Element
    count_in_formula: int     # subíndice (p. ej. 2 en H2O)
    atoms: float
    protons: float
    neutrons: float
    electrons: float
    up_in_protons: float
    down_in_protons: float
    up_in_neutrons: float
    down_in_neutrons: float
    up_mass_mev: float        # masa total de los quarks up (protones + neutrones)
    down_mass_mev: float

    @property
    def nucleon_mass_mev(self) -> float:
        """Masa de todos los protones y neutrones de este elemento."""
        return self.protons * PROTON_MASS_MEV + self.neutrons * NEUTRON_MASS_MEV

    @property
    def quark_mass_mev(self) -> float:
        """Masa en reposo de sus quarks up y down."""
        return self.up_mass_mev + self.down_mass_mev

    @property
    def up_quarks(self) -> float:
        return self.up_in_protons + self.up_in_neutrons

    @property
    def down_quarks(self) -> float:
        return self.down_in_protons + self.down_in_neutrons


@dataclass(frozen=True)
class MoleculeAnalysis:
    """Resultado completo del análisis de una muestra."""
    formula: str
    grams: float
    molar_mass: float         # g/mol
    moles: float
    molecules: float
    elements: list[ElementBreakdown]

    @property
    def total_atoms(self) -> float:
        return sum(e.atoms for e in self.elements)

    @property
    def quark_mass_fraction(self) -> float:
        """Qué parte de la masa de los nucleones aportan las masas de los quarks (~1 %).

        El resto (~99 %) es energía de la interacción fuerte: gluones y movimiento de
        los quarks confinados (E = mc²). Es de donde sale casi toda la masa de la materia.
        """
        nucleons = sum(e.nucleon_mass_mev for e in self.elements)
        quarks = sum(e.quark_mass_mev for e in self.elements)
        return quarks / nucleons if nucleons else 0.0


def validate_formula(formula: str, table: PeriodicTable) -> dict[str, int]:
    """Parsea la fórmula y comprueba que todos los símbolos existen.

    Útil para que la interfaz valide la fórmula ANTES de pedir más datos.
    """
    composition = parse_formula(formula)
    unknown = [s for s in composition if not _has_symbol(table, s)]
    if unknown:
        raise FormulaError(f"Unknown element symbol(s): {', '.join(unknown)}",
                           "unknown_symbols", symbols=unknown)
    return composition


def _has_symbol(table: PeriodicTable, symbol: str) -> bool:
    try:
        table.by_symbol(symbol)
        return True
    except ValueError:
        return False


def molar_mass(composition: dict[str, int], table: PeriodicTable) -> float:
    return sum(table.by_symbol(s).atomic_mass * n for s, n in composition.items())


def analyze(formula: str, grams: float, table: PeriodicTable,
            particles: ParticleCatalog) -> MoleculeAnalysis:
    """Analiza `grams` gramos de la sustancia `formula`."""
    if grams <= 0:
        raise ValueError("The mass in grams must be greater than 0.")

    composition = validate_formula(formula, table)
    mm = molar_mass(composition, table)
    if mm <= 0:
        raise FormulaError(f"The molar mass of {formula} is 0; check the element data.",
                           "zero_molar_mass", formula=formula)

    moles = grams / mm
    molecules = moles * AVOGADRO

    up_mass = particles.find("Up").mass_mev
    down_mass = particles.find("Down").mass_mev

    breakdown = []
    for symbol, count in composition.items():
        el = table.by_symbol(symbol)
        atoms = molecules * count
        protons = atoms * el.protons
        # Media isotópica: en una muestra real de cloro, ~76 % es Cl-35 (18 n) y
        # ~24 % es Cl-37 (20 n), así que hay 18.48 neutrones por átomo de media.
        neutrons = atoms * el.avg_neutrons

        up_p = protons * QUARKS_PER_PROTON["up"]
        down_p = protons * QUARKS_PER_PROTON["down"]
        up_n = neutrons * QUARKS_PER_NEUTRON["up"]
        down_n = neutrons * QUARKS_PER_NEUTRON["down"]

        breakdown.append(ElementBreakdown(
            element=el,
            count_in_formula=count,
            atoms=atoms,
            protons=protons,
            neutrons=neutrons,
            electrons=atoms * el.electrons,
            up_in_protons=up_p,
            down_in_protons=down_p,
            up_in_neutrons=up_n,
            down_in_neutrons=down_n,
            up_mass_mev=(up_p + up_n) * up_mass,
            down_mass_mev=(down_p + down_n) * down_mass,
        ))

    return MoleculeAnalysis(formula, grams, mm, moles, molecules, breakdown)
