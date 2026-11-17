"""Tests de la nucleosíntesis primordial.

Comparan la simulación con valores de referencia: los "fotogramas" de Weinberg,
los resultados de los códigos completos de BBN y las observaciones (PDG 2024).
"""
import math
import random

import pytest

from atomicworld import nuclear_rates as nr
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


def all_fractions(s: nuc.Snapshot) -> list[float]:
    return [s.neutron_fraction, s.proton_fraction, s.deuterium_fraction, s.tritium_fraction,
            s.helium3_fraction, s.helium_fraction, s.lithium7_fraction, s.beryllium7_fraction]


def test_mass_is_conserved():
    for s in RESULT.history[:: 50]:
        assert sum(all_fractions(s)) == pytest.approx(1.0, abs=1e-9)
        assert min(all_fractions(s)) >= 0


def test_detailed_balance_coefficients():
    # p(n,γ)D: REV = (g_n·g_p/g_D)·(m_n·m_p/m_D)^{3/2} con los espines (1/2, 1/2, 1) y las masas
    # en u; Q9 = energía de enlace del deuterio en unidades de 10⁹ K
    name, _r, _p, _f, rev, q9, photon = nr.REACTIONS[0]
    assert name == "p(n,γ)D" and photon
    assert rev == pytest.approx(2 * 2 / 3 * (1.008665 * 1.007825 / 2.014102) ** 1.5, rel=0.005)
    assert q9 == pytest.approx(nuc.DEUTERON_BINDING_MEV * nuc.MEV_TO_KELVIN / 1e9, rel=1e-3)


def test_reactions_conserve_nucleons_and_charge():
    charge = (0, 1, 1, 1, 2, 2, 3, 4)
    for name, reac, prod, *_ in nr.REACTIONS:
        assert sum(nr.MASS_NUMBER[i] for i in reac) == sum(nr.MASS_NUMBER[i] for i in prod), name
        assert sum(charge[i] for i in reac) == sum(charge[i] for i in prod), name


@pytest.mark.parametrize("t9", [0.01, 0.05, 0.1, 0.3, 0.8, 1.5, 3.0, 9.0])
def test_nuclear_rates_are_positive(t9):
    assert all(rate(t9) >= 0 for _n, _r, _p, rate, *_ in nr.REACTIONS)


def test_rate_tables_hit_their_grid_points():
    assert nr.rate_d_p(0.1) == pytest.approx(5.676, rel=1e-9)        # Coc et al. 2015
    assert nr.rate_dd_n(1.0) == pytest.approx(1.442e7, rel=1e-9)


# --- Tasas débiles ---------------------------------------------------------------

def test_weak_rate_is_neutron_decay_when_cold():
    lam_np, lam_pn = nuc.weak_rates(0.003, 878.4)
    assert lam_np == pytest.approx(1 / 878.4, rel=1e-3)
    assert lam_pn < 1e-30


def test_weak_rates_detailed_balance_when_hot():
    # Antes de la aniquilación T_ν = T, y λ(p→n)/λ(n→p) = e^(−Q/T)
    lam_np, lam_pn = nuc.weak_rates(5.0)
    assert lam_pn / lam_np == pytest.approx(math.exp(-nuc.Q_MEV / 5.0), rel=0.01)


def test_weak_rate_grows_as_t5():
    # A T ≫ Q, λ ∝ T⁵ (Weinberg): ×32 al doblar la temperatura
    assert nuc.weak_rates(10.0)[0] / nuc.weak_rates(5.0)[0] == pytest.approx(32, rel=0.1)


# --- Resultados frente a observaciones -----------------------------------------------

def test_primordial_helium():
    assert RESULT.helium_fraction == pytest.approx(nuc.STANDARD_BBN_HELIUM, abs=0.001)
    assert RESULT.helium_fraction == pytest.approx(nuc.OBSERVED_HELIUM, abs=0.003)   # 1σ
    # Sin las correcciones a las tasas débiles, como en el cálculo de Born de PRIMAT (0,2427)
    assert RESULT.helium_fraction_born == pytest.approx(0.2427, abs=0.0005)


def test_deuterium():
    assert RESULT.deuterium_to_hydrogen == pytest.approx(nuc.STANDARD_BBN_D_TO_H, rel=0.07)
    assert RESULT.deuterium_to_hydrogen == pytest.approx(nuc.OBSERVED_D_TO_H, rel=0.05)


def test_helium3():
    assert RESULT.helium3_to_hydrogen == pytest.approx(nuc.STANDARD_BBN_HE3_TO_H, rel=0.05)


def test_lithium7_and_the_lithium_problem():
    li = RESULT.lithium7_to_hydrogen
    assert 4.5e-10 < li < 6.0e-10                       # códigos completos: 4.7–5.5·10⁻¹⁰
    assert li > 3 * nuc.OBSERVED_LI7_TO_H               # el problema del litio
    # A 3.5 h casi todo el litio es todavía ⁷Be (luego captura un electrón)
    assert RESULT.final.beryllium7_fraction > RESULT.final.lithium7_fraction


@pytest.mark.parametrize("eta, alterbbn", [
    # AlterBBN 2.2 (Arbey et al. 2018), alter_etannutau.x η 3 0 878.4: D/H, ³He/H, ⁷Li/H
    (6.1e-10, (2.325e-5, 1.022e-5, 5.686e-10)),
    (3e-10, (7.186e-5, 1.582e-5, 1.367e-10)),
    (1e-9, (9.706e-6, 7.857e-6, 1.338e-9)),
])
def test_agrees_with_alterbbn(eta, alterbbn):
    result = RESULT if eta == nuc.DEFAULT_ETA else nuc.simulate(eta=eta)
    d, he3, li = alterbbn
    assert result.deuterium_to_hydrogen == pytest.approx(d, rel=0.06)
    assert result.helium3_to_hydrogen == pytest.approx(he3, rel=0.03)
    assert result.lithium7_to_hydrogen == pytest.approx(li, rel=0.08)


def test_numerical_convergence():
    fine = nuc.simulate(steps=5000)
    assert RESULT.deuterium_to_hydrogen == pytest.approx(fine.deuterium_to_hydrogen, rel=0.003)
    assert RESULT.lithium7_to_hydrogen == pytest.approx(fine.lithium7_to_hydrogen, rel=0.003)


def test_more_neutrino_species_more_helium():
    ys = [nuc.simulate(neutrino_species=n, steps=800).helium_fraction for n in (2, 3, 4)]
    assert ys[0] < ys[1] < ys[2]
    assert ys[2] - ys[1] == pytest.approx(0.013, abs=0.003)   # sensibilidad conocida ΔY/ΔN_ν


def test_more_baryons_more_helium_less_deuterium():
    low = nuc.simulate(eta=3e-10, steps=800)
    high = nuc.simulate(eta=1e-9, steps=800)
    assert high.helium_fraction > low.helium_fraction
    assert high.deuterium_to_hydrogen < low.deuterium_to_hydrogen
    assert high.helium3_to_hydrogen < low.helium3_to_hydrogen
    assert high.lithium7_to_hydrogen > low.lithium7_to_hydrogen      # rama del ⁷Be


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
