"""Tests de los datos nuevos para el visor 3D: configuración electrónica, radios e isótopos."""
import math
import re

import pytest

from atomicworld.repository import IsotopeTable, PeriodicTable

TABLE = PeriodicTable()
ISOTOPES = IsotopeTable()
YEAR = 365.25 * 86400
L_CAPACITY = {"s": 2, "p": 6, "d": 10, "f": 14}
NOBLE = {"He": 2, "Ne": 10, "Ar": 18, "Kr": 36, "Xe": 54, "Rn": 86}


def electrons_in(config: str) -> int:
    total = 0
    for part in config.split():
        if part.startswith("["):
            total += NOBLE[part.strip("[]")]
        else:
            m = re.fullmatch(r"([1-7])([spdf])(\d+)", part)
            assert m, part
            assert int(m.group(3)) <= L_CAPACITY[m.group(2)], part
            total += int(m.group(3))
    return total


# --- Elementos ------------------------------------------------------------------

def test_configuration_has_one_electron_per_proton():
    for e in TABLE:
        assert electrons_in(e.electron_config) == e.protons, e.name


@pytest.mark.parametrize("symbol, config", [
    ("H", "1s1"),
    ("Fe", "[Ar] 3d6 4s2"),
    ("Cr", "[Ar] 3d5 4s1"),     # excepción a la regla de llenado
    ("Cu", "[Ar] 3d10 4s1"),    # excepción
    ("Pd", "[Kr] 4d10"),        # excepción: sin electrones 5s
])
def test_known_configurations(symbol, config):
    assert TABLE.find(symbol).electron_config == config


def test_every_element_has_size_and_color():
    for e in TABLE:
        assert 100 <= e.vdw_radius_pm <= 350, e.name
        assert re.fullmatch(r"#[0-9a-f]{6}", e.color), e.name


def test_only_superheavy_radii_are_estimated():
    assert [e.number for e in TABLE if e.vdw_estimated] == list(range(104, 119))


# --- Isótopos -------------------------------------------------------------------

def test_there_are_thousands_of_isotopes_for_every_element():
    assert len(ISOTOPES) > 3000
    assert all(ISOTOPES.of(e.number) for e in TABLE)


def test_table_isotope_exists_and_is_the_most_abundant():
    for e in TABLE:
        iso = ISOTOPES.default(e)
        assert iso.neutrons == e.neutrons, e.name
        natural = ISOTOPES.natural(e.number)
        if natural:
            assert natural[0] is iso, e.name


def test_natural_abundances_add_up_to_100():
    for e in TABLE:
        natural = ISOTOPES.natural(e.number)
        if natural:
            assert sum(i.abundance for i in natural) == pytest.approx(100, abs=0.1), e.name


def test_stable_isotopes_have_no_half_life():
    # Te-123: la fuente lo da por estable pero conserva una captura electrónica antigua
    # (hoy solo hay una cota: semivida > 10¹⁶ años).
    for i in ISOTOPES:
        if i.is_stable:
            assert i.half_life_s is None, (i.z, i.a)
            assert not i.decay or (i.z, i.a) == (52, 123), (i.z, i.a)


def test_isotope_mass_close_to_mass_number():
    # cada nucleón pesa ≈ 1 u; la energía de enlace aparta la masa hasta ~0,2 u en los superpesados
    assert all(abs(i.mass_u - i.a) < 0.25 for i in ISOTOPES)


@pytest.mark.parametrize("z, a, years, mode", [
    (6, 14, 5_700, "B-"),           # carbono-14 (datación)
    (1, 3, 12.32, "B-"),            # tritio
    (92, 235, 7.04e8, "A"),         # uranio-235
    (92, 238, 4.463e9, "A"),        # uranio-238
    (94, 239, 24_110, "A"),         # plutonio-239
    (19, 40, 1.248e9, "B-"),        # potasio-40, el del plátano
])
def test_famous_radioactive_isotopes(z, a, years, mode):
    iso = ISOTOPES.get(z, a)
    assert iso.status == "radioactive"
    assert iso.half_life_s / YEAR == pytest.approx(years, rel=0.01)
    assert iso.main_decay.mode == mode


def test_potassium_40_has_two_known_branches():
    k40 = ISOTOPES.get(19, 40)
    assert [(m.mode, m.intensity) for m in k40.decay] == [("B-", 89.28), ("B+", 10.72)]


def test_unreliable_minor_intensities_are_dropped():
    # en la fuente, la fisión espontánea del U-235 sale como 7 % (es 7·10⁻⁹ %)
    u235 = ISOTOPES.get(92, 235)
    assert u235.decay[0].intensity == 100
    assert all(m.intensity is None for m in u235.decay[1:])


def test_known_intensities_never_exceed_100():
    for i in ISOTOPES:
        known = [m.intensity for m in i.decay if m.intensity is not None]
        assert sum(known) <= 100.5, (i.z, i.a)


def test_unknown_isotope_raises():
    with pytest.raises(ValueError):
        ISOTOPES.get(6, 99)


def test_half_lives_span_the_whole_range():
    lives = [i.half_life_s for i in ISOTOPES if i.half_life_s]
    assert min(lives) < 1e-21 and max(lives) > 1e24 * YEAR / 10
    assert all(math.isfinite(x) and x > 0 for x in lives)
