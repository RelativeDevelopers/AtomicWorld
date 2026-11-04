"""Tests de atoms.py (configuración, Slater, núcleo) y de los nombres en varios idiomas."""
import pytest

from atomicworld import atoms, names
from atomicworld.repository import ParticleCatalog, PeriodicTable

TABLE = PeriodicTable()
PARTICLES = ParticleCatalog()


# --- Configuración electrónica ----------------------------------------------------

def test_parse_expands_noble_gas_core():
    assert atoms.full_config(TABLE.find("Fe")) == "1s2 2s2 2p6 3s2 3p6 3d6 4s2"


def test_every_element_parses_and_counts_its_electrons():
    for e in TABLE:
        assert sum(s.electrons for s in atoms.subshells(e)) == e.electrons, e.name


def test_subshells_are_ordered_from_inside_out():
    shells = atoms.subshells(TABLE.find("Au"))
    assert [(s.n, s.l) for s in shells] == sorted((s.n, s.l) for s in shells)


@pytest.mark.parametrize("bad", ["1s3", "2d1", "[Zz] 1s1", "3x2", "1p1"])
def test_invalid_configurations_are_rejected(bad):
    with pytest.raises(atoms.ConfigError):
        atoms.parse_config(bad)


def test_valence_shell_is_the_period():
    assert [atoms.valence_shell(TABLE.find(s)) for s in ("H", "C", "Na", "Fe", "Au", "Og")] == [1, 2, 3, 4, 6, 7]


# --- Reglas de Slater: valores de los libros de química ------------------------

@pytest.mark.parametrize("symbol, n, l, zeff", [
    ("H", 1, 0, 1.00),
    ("He", 1, 0, 1.70),
    ("C", 2, 1, 3.25),
    ("N", 2, 1, 3.90),
    ("O", 2, 1, 4.55),
    ("Na", 3, 0, 2.20),
    ("Fe", 4, 0, 3.75),
    ("Fe", 3, 1, 14.75),
    ("Fe", 3, 2, 6.25),
    ("Zn", 4, 0, 4.35),
    ("Zn", 3, 2, 8.85),
])
def test_slater_textbook_values(symbol, n, l, zeff):
    el = TABLE.find(symbol)
    assert atoms.slater_zeff(el.protons, atoms.subshells(el), n, l) == pytest.approx(zeff)


def test_zeff_is_positive_and_below_z_for_every_electron():
    for e in TABLE:
        shells = atoms.subshells(e)
        for s in shells:
            assert 0 < atoms.slater_zeff(e.protons, shells, s.n, s.l) <= e.protons, (e.name, s.name)


def test_inner_electrons_feel_more_charge():
    u = TABLE.find("U")
    shells = atoms.subshells(u)
    assert atoms.slater_zeff(92, shells, 1, 0) > atoms.slater_zeff(92, shells, 7, 0)


def test_empty_subshell_raises():
    c = TABLE.find("C")
    with pytest.raises(ValueError):
        atoms.slater_zeff(6, atoms.subshells(c), 3, 0)


# --- Núcleo ------------------------------------------------------------------------

def test_nuclear_radius():
    assert atoms.nuclear_radius_fm(1) == pytest.approx(1.2)
    assert atoms.nuclear_radius_fm(27) == pytest.approx(3.6)


def test_atom_is_tens_of_thousands_of_times_bigger_than_its_nucleus():
    for e in TABLE:
        assert 10_000 < atoms.atom_to_nucleus_ratio(e) < 150_000, e.name


# --- Nombres en varios idiomas -------------------------------------------------

def test_every_language_names_everything():
    for lang in names.LANGUAGES:
        t = names.table(lang)
        assert set(t["elements"]) == {str(e.number) for e in TABLE}
        assert set(t["particles"]) == {p.name for p in PARTICLES}
        assert set(t["families"]) == {p.family for p in PARTICLES}
        assert all(v.strip() for v in t["elements"].values())


@pytest.mark.parametrize("number, en, es, ca", [
    (26, "Iron", "Hierro", "Ferro"),
    (79, "Gold", "Oro", "Or"),
    (1, "Hydrogen", "Hidrógeno", "Hidrogen"),
])
def test_element_names(number, en, es, ca):
    assert [names.element(number, l) for l in ("en", "es", "ca")] == [en, es, ca]


@pytest.mark.parametrize("text", ["Hierro", "iron", "FERRO", "Fe", "26", "  fe "])
def test_search_in_any_language(text):
    assert TABLE.find(text).symbol == "Fe"


@pytest.mark.parametrize("text, symbol", [
    ("Fosforo", "P"), ("fósforo", "P"), ("Estano", "Sn"), ("Estaño", "Sn"), ("Or", "Au"),
])
def test_search_ignores_accents(text, symbol):
    assert TABLE.find(text).symbol == symbol


def test_particles_found_in_any_language():
    assert PARTICLES.find("Electrón") is PARTICLES.find("Electron")
    assert PARTICLES.find("boson de higgs").name == "Higgs boson"


def test_unknown_language():
    with pytest.raises(ValueError):
        names.element(1, "fr")
