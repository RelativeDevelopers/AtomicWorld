import pytest

from atomicworld.chemistry import FormulaError, analyze, parse_formula
from atomicworld.constants import AVOGADRO
from atomicworld.repository import ParticleCatalog, PeriodicTable

TABLE = PeriodicTable()
PARTICLES = ParticleCatalog()


@pytest.mark.parametrize("formula, expected", [
    ("H2O", {"H": 2, "O": 1}),
    ("CO2", {"C": 1, "O": 2}),
    ("NaCl", {"Na": 1, "Cl": 1}),
    ("C6H12O6", {"C": 6, "H": 12, "O": 6}),
    ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}),
    ("CH3COOH", {"C": 2, "H": 4, "O": 2}),
    ("Al2(SO4)3", {"Al": 2, "S": 3, "O": 12}),
    ("Fe", {"Fe": 1}),
])
def test_parse_formula(formula, expected):
    assert parse_formula(formula) == expected


@pytest.mark.parametrize("bad", ["", "   ", "h2o", "2H", "H2O)", "(H2O", "()", "H0", "H-O"])
def test_parse_formula_rejects_invalid(bad):
    with pytest.raises(FormulaError):
        parse_formula(bad)


def test_unknown_symbol():
    with pytest.raises(FormulaError):
        analyze("Xx2", 1.0, TABLE, PARTICLES)


def test_water_one_mole():
    # 18.015 g de agua ≈ 1 mol ≈ 6.022e23 moléculas
    result = analyze("H2O", 18.015, TABLE, PARTICLES)
    assert result.moles == pytest.approx(1.0, rel=1e-4)
    assert result.molecules == pytest.approx(AVOGADRO, rel=1e-4)
    assert result.total_atoms == pytest.approx(3 * AVOGADRO, rel=1e-4)


def test_oxygen_quarks_use_neutrons():
    # 1 mol de O: 8 p y ~8.004 n de media (O-16, O-17, O-18)
    result = analyze("O", TABLE.find("O").atomic_mass, TABLE, PARTICLES)
    o = result.elements[0]
    n = TABLE.find("O").avg_neutrons
    assert n == pytest.approx(8.0, abs=0.01)
    assert o.up_in_neutrons == pytest.approx(n * AVOGADRO, rel=1e-9)
    assert o.down_in_neutrons == pytest.approx(2 * n * AVOGADRO, rel=1e-9)
    assert o.up_quarks == pytest.approx((16 + n) * AVOGADRO, rel=1e-9)
    assert o.electrons == o.protons


def test_quarks_are_about_one_percent_of_nucleon_mass():
    result = analyze("H2O", 18, TABLE, PARTICLES)
    assert 0.005 < result.quark_mass_fraction < 0.015


def test_mercury_lookup_no_longer_shifted():
    # En el original, "Mercury" devolvía el Talio y "Lead" el Bismuto.
    assert analyze("Hg", 200.592, TABLE, PARTICLES).elements[0].element.name == "Mercury"
    assert analyze("Pb", 207.2, TABLE, PARTICLES).elements[0].element.name == "Lead"


def test_negative_mass_rejected():
    with pytest.raises(ValueError):
        analyze("H2O", -5, TABLE, PARTICLES)


def test_lookup_is_case_insensitive():
    assert TABLE.find("oxygen").symbol == "O"
    assert TABLE.find("  FE ").name == "Iron"


@pytest.mark.parametrize("bad, code", [
    ("", "empty_formula"),
    ("H-O", "unexpected_character"),
    ("H2O)", "unmatched_closing"),
    ("()", "empty_parentheses"),
    ("2H", "nothing_to_multiply"),
    ("H0", "zero_subscript"),
    ("(H2O", "unclosed_parenthesis"),
])
def test_formula_errors_have_codes(bad, code):
    """Cada error lleva un código para que la web lo traduzca."""
    with pytest.raises(FormulaError) as info:
        parse_formula(bad)
    assert info.value.code == code
    assert info.value.to_dict()["code"] == code


def test_unknown_symbols_error_lists_them():
    from atomicworld.chemistry import validate_formula
    with pytest.raises(FormulaError) as info:
        validate_formula("XyH2Qq", TABLE)
    assert info.value.code == "unknown_symbols"
    assert info.value.params == {"symbols": ["Xy", "Qq"]}
