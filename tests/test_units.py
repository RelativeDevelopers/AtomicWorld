"""Tests del conversor de masas (antes StandardModelConversor.py).

Los valores en kg se comparan con CODATA 2022, que los da medidos directamente:
si el conversor y las constantes son correctos, tienen que coincidir.
"""
import pytest

from atomicworld import units
from atomicworld.repository import ParticleCatalog

PARTICLES = ParticleCatalog()


def test_ev_to_kg_factor_is_exact_si():
    assert units.EV_IN_KG == pytest.approx(1.78266192e-36, rel=1e-8)


@pytest.mark.parametrize("name, kg", [
    ("Electron", 9.1093837139e-31),      # CODATA 2022
    ("Muon", 1.883531627e-28),
    ("Tau", 3.16754e-27),
])
def test_particle_masses_in_kg(name, kg):
    p = PARTICLES.find(name)
    assert units.mev_to_kg(p.mass_mev) == pytest.approx(kg, rel=1e-4)


def test_proton_in_kg_and_u():
    proton = units.Mass(938.27208816)
    assert proton.kg == pytest.approx(1.67262192e-27, rel=1e-7)
    assert proton.to("u") == pytest.approx(1.007276467, rel=1e-8)
    assert proton.proton_masses == pytest.approx(1.0, rel=1e-6)


def test_atomic_mass_unit_consistency():
    # 1 u en kg (CODATA 2022) tiene que salir de 931.494 MeV/c²
    assert units.convert(1, "u", "kg") == pytest.approx(1.66053906892e-27, rel=1e-9)


def test_higgs_in_kg():
    assert units.convert(125.2, "GeV", "kg") == pytest.approx(2.2319e-25, rel=1e-4)


@pytest.mark.parametrize("unit", list(units.UNITS_IN_MEV))
def test_round_trip(unit):
    assert units.convert(units.convert(3.7, unit, "kg"), "kg", unit) == pytest.approx(3.7, rel=1e-12)


def test_energy_prefixes():
    assert units.convert(1, "GeV", "MeV") == 1000
    assert units.convert(1, "TeV", "keV") == pytest.approx(1e9)
    assert units.convert(1000, "g", "kg") == pytest.approx(1.0)


def test_unknown_unit():
    with pytest.raises(units.UnitError) as info:
        units.convert(1, "lb", "kg")
    assert info.value.code == "unknown_unit" and info.value.params == {"unit": "lb"}


@pytest.mark.parametrize("bad", [-1, float("inf"), float("nan")])
def test_invalid_mass(bad):
    with pytest.raises(ValueError):
        units.Mass(bad)


def test_symbols_and_best_unit():
    assert units.symbol("MeV") == "MeV/c²" and units.symbol("kg") == "kg"
    assert units.best_energy_unit(0.511) == "keV"
    assert units.best_energy_unit(125_200) == "GeV"
    assert units.best_energy_unit(4.5e-7) == "eV"


def test_every_particle_is_converted():
    rows = units.particle_masses(PARTICLES)
    assert len(rows) == len(PARTICLES)
    massless = {r.particle.name for r in rows if r.is_massless}
    assert massless == {"Gluon", "Photon", "Graviton"}


def test_closest_particle():
    particle, ratio = units.closest_particle(units.Mass.of(1.8, "GeV"), PARTICLES)
    assert particle.name == "Tau" and ratio == pytest.approx(1.013, abs=1e-3)
    # Los neutrinos (solo cota superior) no cuentan: 1 eV se compara con el electrón
    assert units.closest_particle(units.Mass.of(1, "eV"), PARTICLES)[0].name == "Electron"
    assert units.closest_particle(units.Mass(0), PARTICLES) is None
