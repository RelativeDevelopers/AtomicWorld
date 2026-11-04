"""Comprobaciones de coherencia de los datos.

Estos tests protegen las correcciones hechas con tools/build_data.py:
si alguien edita los JSON y rompe algo, pytest lo detecta.
"""
import pytest

from atomicworld.repository import ParticleCatalog, PeriodicTable

TABLE = PeriodicTable()
PARTICLES = ParticleCatalog()


# --- Tabla periódica ---------------------------------------------------------

def test_all_118_elements_present():
    assert [e.number for e in TABLE] == list(range(1, 119))


def test_symbols_and_names_are_unique():
    assert len({e.symbol for e in TABLE}) == 118
    assert len({e.name for e in TABLE}) == 118


def test_protons_equal_atomic_number():
    assert all(e.protons == e.number for e in TABLE)


def test_all_masses_positive():
    assert all(e.atomic_mass > 0 for e in TABLE)


def test_mass_number_close_to_atomic_mass():
    # El número másico del isótopo principal no puede alejarse mucho del peso atómico.
    for e in TABLE:
        assert abs(e.mass_number - e.atomic_mass) < 3, e.name


def test_average_neutrons_consistent_with_mass():
    # peso atómico ≈ Z + N medio (cada nucleón ≈ 1 u), con margen por la energía de enlace
    for e in TABLE:
        assert abs(e.protons + e.avg_neutrons - e.atomic_mass) < 1.2, e.name


def test_melting_below_boiling():
    exceptions = {"Arsenic"}  # sublima a 1 atm: su "ebullición" es una sublimación
    for e in TABLE:
        if e.melting_c is not None and e.boiling_c is not None and e.name not in exceptions:
            assert e.melting_c < e.boiling_c, e.name


@pytest.mark.parametrize("name, symbol, mass, neutrons", [
    ("Hydrogen", "H", 1.008, 0),
    ("Carbon", "C", 12.011, 6),
    ("Chlorine", "Cl", 35.45, 18),
    ("Copper", "Cu", 63.546, 34),
    ("Rhenium", "Re", 186.207, 112),
    ("Mercury", "Hg", 200.592, 122),
    ("Lead", "Pb", 207.2, 126),
    ("Uranium", "U", 238.029, 146),
    ("Oganesson", "Og", 294, 176),
])
def test_reference_elements(name, symbol, mass, neutrons):
    e = TABLE.find(name)
    assert e.symbol == symbol
    assert e.atomic_mass == pytest.approx(mass, abs=0.01)
    assert e.neutrons == neutrons


def test_chlorine_isotope_average():
    # ~75.8 % Cl-35 (18 n) + ~24.2 % Cl-37 (20 n)
    assert TABLE.find("Cl").avg_neutrons == pytest.approx(18.48, abs=0.01)


def test_aliases():
    assert TABLE.find("Aluminum").symbol == "Al"
    assert TABLE.find("cesium").symbol == "Cs"


# --- Partículas ----------------------------------------------------------------

def test_particle_binaries_are_unique_bytes():
    codes = [p.binary for p in PARTICLES]
    assert len(codes) == len(set(codes))
    assert all(len(b) == 8 and set(b) <= {"0", "1"} for b in codes)


def test_particle_names_are_unique():
    assert len({p.name for p in PARTICLES}) == len(PARTICLES)


def test_neutrino_masses_are_upper_limits():
    nu_e = PARTICLES.find("Electron neutrino")
    assert nu_e.mass_is_upper_limit and nu_e.mass_mev < 1e-6      # < 1 eV
    for p in PARTICLES:
        assert p.mass_is_upper_limit == ("neutrino" in p.name.lower()), p.name


def test_graviton_is_hypothetical_spin_2():
    g = PARTICLES.find("Graviton")
    assert g.hypothetical and g.spin == 2
    assert [p.name for p in PARTICLES if p.hypothetical] == ["Graviton"]


def test_antiparticles_have_opposite_charge_and_same_mass():
    pairs = [("Up", "Anti-up"), ("Down", "Anti-down"), ("Top", "Anti-top"),
             ("Electron", "Positron"), ("Muon", "Antimuon"), ("Tau", "Antitau")]
    for a, b in pairs:
        pa, pb = PARTICLES.find(a), PARTICLES.find(b)
        assert pa.charge == -pb.charge and pa.mass_mev == pb.mass_mev, a


def test_proton_and_neutron_charge_from_quarks():
    up, down = PARTICLES.find("Up").charge, PARTICLES.find("Down").charge
    assert 2 * up + down == 1      # protón uud
    assert up + 2 * down == 0      # neutrón udd


@pytest.mark.parametrize("name, gev", [
    ("Top", 172.57), ("Z boson", 91.1876), ("W+ boson", 80.3692), ("Higgs boson", 125.20),
])
def test_heavy_particle_masses(name, gev):
    assert PARTICLES.find(name).mass_mev == pytest.approx(gev * 1000, rel=1e-4)
