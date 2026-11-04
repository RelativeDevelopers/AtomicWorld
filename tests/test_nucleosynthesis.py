"""Tests de la nucleosíntesis primordial.

Comparan la simulación con valores de referencia: los "fotogramas" de Weinberg,
los resultados de los códigos completos de BBN y las observaciones (PDG 2024).
"""
import math
import random

import pytest

from atomicworld import nucleosynthesis as nuc

RESULT = nuc.simulate()


# --- Termodinámica y expansión ---------------------------------------------------

def test_electron_factors_limits():
    assert nuc.electron_factors(50.0) == pytest.approx((1.0, 1.0), abs=1e-3)   # T ≫ m_e
    assert nuc.electron_factors(0.005) == (0.0, 0.0)                          # T ≪ m_e


def test_neutrino_temperature_after_annihilation():
    # Al final T_ν/T = (4/11)^(1/3) ≈ 0.714: el famoso fondo de neutrinos a 1.95 K
    assert nuc.neutrino_temperature_ratio(0.01) == pytest.approx((4 / 11) ** (1 / 3), rel=1e-3)
    assert nuc.neutrino_temperature_ratio(10.0) == pytest.approx(1.0, abs=1e-3)


def test_time_temperature_relation():
    # Antes de la aniquilación: t ≈ 0.74 s / T²(MeV); después: t ≈ 1.32 s / T²
    early = RESULT.at_temperature(3.0)
    late = RESULT.at_temperature(0.03)
    assert early.time_s * early.temperature_mev ** 2 == pytest.approx(0.74, rel=0.03)
    assert late.time_s * late.temperature_mev ** 2 == pytest.approx(1.32, rel=0.03)


@pytest.mark.parametrize("frame, weinberg_time_s", [
    ("First frame", 0.0108),
    ("Second frame", 0.11),
    ("Third frame", 1.09),
    ("Fourth frame", 13.82),
    ("Fifth frame", 182),        # "3 minutos y 2 segundos"
    ("Sixth frame", 2080),       # "34 minutos y 40 segundos"
])
def test_weinberg_frames_times(frame, weinberg_time_s):
    snap = RESULT.at_temperature(nuc.WEINBERG_FRAMES_K[frame] / nuc.MEV_TO_KELVIN)
    assert snap.time_s == pytest.approx(weinberg_time_s, rel=0.10)


@pytest.mark.parametrize("frame, weinberg_neutrons", [
    ("Second frame", 0.38),
    ("Third frame", 0.24),
    ("Fourth frame", 0.17),
])
def test_weinberg_frames_neutron_fraction(frame, weinberg_neutrons):
    snap = RESULT.at_temperature(nuc.WEINBERG_FRAMES_K[frame] / nuc.MEV_TO_KELVIN)
    assert snap.neutron_fraction == pytest.approx(weinberg_neutrons, abs=0.01)


# --- Física nuclear ------------------------------------------------------------------

def test_equilibrium_at_high_temperature():
    assert RESULT.history[0].neutron_fraction == pytest.approx(
        RESULT.history[0].equilibrium_fraction, rel=1e-3)


def test_freeze_out_ratio_about_one_sixth():
    # Tras la congelación, antes de que la desintegración pese: n/p ≈ 1/5 – 1/6
    snap = RESULT.at_temperature(0.25)
    assert 1 / 6.5 < snap.neutron_to_proton < 1 / 4.5


def test_np_to_deuteron_rate():
    assert nuc.rate_np_to_d(0.08) == pytest.approx(4.4e-20, rel=0.05)


def test_deuterium_bottleneck_timing():
    snap = RESULT.event("nucleosynthesis").snapshot
    assert 0.06 < snap.temperature_mev < 0.09          # ~0.7–1·10⁹ K
    assert 150 < snap.time_s < 300                      # "unos tres minutos"


def test_mass_is_conserved():
    for s in RESULT.history[:: 50]:
        total = s.neutron_fraction + s.proton_fraction + s.deuterium_fraction + s.helium_fraction
        assert total == pytest.approx(1.0, abs=1e-9)
        assert min(s.neutron_fraction, s.proton_fraction, s.deuterium_fraction, s.helium_fraction) >= 0


# --- Resultados frente a observaciones -----------------------------------------------

def test_primordial_helium():
    assert RESULT.helium_fraction == pytest.approx(nuc.STANDARD_BBN_HELIUM, abs=0.006)
    assert RESULT.helium_fraction == pytest.approx(nuc.OBSERVED_HELIUM, abs=0.006)


def test_deuterium_order_of_magnitude():
    assert 1e-5 < RESULT.deuterium_to_hydrogen < 6e-5


def test_more_neutrino_species_more_helium():
    ys = [nuc.simulate(neutrino_species=n, steps=800).helium_fraction for n in (2, 3, 4)]
    assert ys[0] < ys[1] < ys[2]
    assert ys[2] - ys[1] == pytest.approx(0.013, abs=0.003)   # sensibilidad conocida ΔY/ΔN_ν


def test_more_baryons_more_helium_less_deuterium():
    low = nuc.simulate(eta=3e-10, steps=800)
    high = nuc.simulate(eta=1e-9, steps=800)
    assert high.helium_fraction > low.helium_fraction
    assert high.deuterium_to_hydrogen < low.deuterium_to_hydrogen


def test_longer_neutron_lifetime_more_helium():
    assert (nuc.simulate(neutron_lifetime_s=900, steps=800).helium_fraction
            > nuc.simulate(neutron_lifetime_s=860, steps=800).helium_fraction)


@pytest.mark.parametrize("kwargs", [{"eta": 0}, {"eta": 1}, {"neutron_lifetime_s": 0},
                                    {"neutrino_species": -1}])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        nuc.simulate(**kwargs)


# --- Modo partícula a partícula -----------------------------------------------------

def test_particles_conserve_nucleons():
    counts = nuc.simulate_particles(500, rng=random.Random(3))
    assert all(c.total == 500 for c in counts)
    assert counts[-1].neutrons == 0                     # ninguno queda libre al final


def test_particles_converge_to_exact_result():
    last = nuc.simulate_particles(200_000, rng=random.Random(7))[-1]
    assert last.helium_fraction == pytest.approx(RESULT.helium_fraction, abs=0.01)


def test_particles_reproducible_with_seed():
    a = nuc.simulate_particles(300, rng=random.Random(42))[-1]
    b = nuc.simulate_particles(300, rng=random.Random(42))[-1]
    assert a == b


def test_timeline_is_ordered():
    times = [snap.time_s for _t, _d, snap in nuc.timeline(RESULT)]
    assert times == sorted(times) and len(times) == 9
    assert not math.isnan(times[0])
