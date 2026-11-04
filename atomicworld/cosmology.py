"""Nucleosíntesis primordial: "Los tres primeros minutos" (Weinberg, 1977).

Modelo semianalítico del universo entre ~0.01 s y ~5 minutos tras el Big Bang:

1. Expansión: el universo está dominado por radiación (fotones, electrones,
   positrones y neutrinos). La ecuación de Friedmann da el ritmo de expansión H,
   y de ahí la relación entre tiempo y temperatura.
2. Aniquilación e⁺e⁻: cuando la temperatura baja de ~0.5 MeV, electrones y
   positrones se aniquilan y calientan los fotones (pero no a los neutrinos,
   que ya se habían desacoplado). Por eso hoy T_ν/T_γ = (4/11)^(1/3).
3. Equilibrio n ↔ p: las reacciones débiles (n + ν ↔ p + e⁻, etc.) mantienen
   n/p = e^(−Q/T) hasta que la expansión es más rápida que ellas (~1 s, ~0.8 MeV).
   Entonces la proporción se "congela" en torno a 1/6.
4. Desintegración del neutrón: los neutrones libres siguen desintegrándose
   (vida media ~880 s) mientras esperan.
5. Cuello de botella del deuterio: el deuterio (p + n) se forma, pero los
   fotones, mil millones por cada barión, lo rompen. Solo cuando T ≈ 0.07 MeV
   (~3 minutos) sobrevive, y casi todos los neutrones acaban en helio-4.

Resultado: fracción de masa de helio-4 Y ≈ 2·X_n ≈ 0.25, como se observa.

Limitaciones (es un modelo didáctico): no incluye una red de reacciones nucleares,
así que no calcula deuterio, helio-3 ni litio residuales, y las tasas débiles se calculan
en aproximación de Born (sin correcciones coulombianas ni radiativas, que suben Y
en ~0.005). Aun así, Y sale con un error de ~2 %.

Unidades internas: MeV para energías y temperaturas, segundos para el tiempo
(sistema natural ħ = c = k_B = 1).
"""
from dataclasses import dataclass, field

import numpy as np

# --- Constantes -----------------------------------------------------------------

HBAR_MEV_S = 6.582119569e-22        # ħ en MeV·s
PLANCK_MASS_MEV = 1.220890e22       # masa de Planck en MeV
ELECTRON_MASS_MEV = 0.51099895
NEUTRON_PROTON_DIFF_MEV = 1.29333236   # Q = m_n − m_p
DEUTERON_BINDING_MEV = 2.224566     # energía de enlace del deuterio
NUCLEON_MASS_MEV = 938.92           # media protón-neutrón
MEV_TO_KELVIN = 1.160451812e10

NEUTRON_LIFETIME_S = 878.4          # PDG 2024
BARYON_TO_PHOTON = 6.1e-10          # η, de Planck / abundancia de deuterio
NEUTRINO_FAMILIES = 3

_ZETA3 = 1.2020569


# --- Termodinámica de electrones y positrones -------------------------------------

_X = np.linspace(1e-6, 40.0, 4000)   # p/T para las integrales de Fermi-Dirac


def _electron_positron(T: float) -> tuple[float, float]:
    """Densidad de energía y entropía de e⁺e⁻ (4 estados de espín/carga) a temperatura T."""
    y = ELECTRON_MASS_MEV / T
    e = np.sqrt(_X**2 + y**2)
    occupation = 1.0 / (np.exp(e) + 1.0)
    rho = 4 / (2 * np.pi**2) * T**4 * np.trapezoid(_X**2 * e * occupation, _X)
    pressure = 4 / (2 * np.pi**2) * T**4 * np.trapezoid(_X**4 / (3 * e) * occupation, _X)
    return rho, (rho + pressure) / T


# --- Historia térmica: T(t) y T_ν(t) ----------------------------------------------

@dataclass
class ThermalHistory:
    temperature: np.ndarray        # temperatura de los fotones, MeV (decreciente)
    neutrino_temperature: np.ndarray
    time: np.ndarray               # segundos
    hubble: np.ndarray             # ritmo de expansión, 1/s


def thermal_history(neutrino_families: float = NEUTRINO_FAMILIES,
                    t_start_mev: float = 30.0, t_end_mev: float = 0.01,
                    points: int = 3000) -> ThermalHistory:
    """Integra la ecuación de Friedmann conservando la entropía de γ + e⁺e⁻.

    Los neutrinos se tratan como desacoplados desde el principio (T_ν = T al inicio)
    y solo se enfrían con la expansión: T_ν ∝ 1/a.
    """
    T = np.geomspace(t_start_mev, t_end_mev, points)
    s_high = (2 + 7 / 8 * 4) * 2 * np.pi**2 / 45      # entropía/T³ de γ+e± relativistas

    rho_e, s_e = np.array([_electron_positron(t) for t in T]).T
    s_gamma = 4 * np.pi**2 / 45 * T**3
    # Conservación de la entropía comóvil: a³·s(T) = cte, con a = 1/T_ν
    t_nu = ((s_gamma + s_e) / s_high) ** (1 / 3)

    rho = (np.pi**2 / 15 * T**4                            # fotones
           + rho_e                                         # electrones y positrones
           + neutrino_families * 7 / 8 * np.pi**2 / 15 * t_nu**4)   # neutrinos
    hubble = np.sqrt(8 * np.pi * rho / 3) / PLANCK_MASS_MEV      # en MeV
    hubble_s = hubble / HBAR_MEV_S                                # en 1/s

    # dt = d(ln a) / H, con ln a = −ln T_ν
    ln_a = -np.log(t_nu)
    integrand = 1 / hubble_s
    time = np.empty_like(T)
    time[0] = 1 / (2 * hubble_s[0])                     # era de radiación: t = 1/(2H)
    time[1:] = time[0] + np.cumsum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(ln_a))
    return ThermalHistory(T, t_nu, time, hubble_s)


# --- Reacciones débiles n ↔ p -----------------------------------------------------
# Integrales de Born (Weinberg, "Gravitation and Cosmology", §15.6; Bernstein,
# Brown y Feinberg 1989). Las seis reacciones:
#   n + ν  → p + e⁻        p + e⁻ → n + ν
#   n + e⁺ → p + ν̄         p + ν̄  → n + e⁺
#   n → p + e⁻ + ν̄  (desintegración libre)
# Los electrones siguen Fermi-Dirac a T (fotones) y los neutrinos a T_ν.
# La normalización se fija con la vida media del neutrón: a T → 0 solo queda
# la desintegración y su tasa debe ser 1/τ_n.

_Q = NEUTRON_PROTON_DIFF_MEV
_ME = ELECTRON_MASS_MEV


def _fermi(energy, temperature):
    return 1.0 / (np.exp(np.clip(energy / temperature, -700, 700)) + 1.0)


def _p(e):
    return np.sqrt(np.maximum(e**2 - _ME**2, 0.0))


_E_DECAY = np.linspace(_ME, _Q, 400)
_DECAY_PHASE_SPACE = np.trapezoid(_p(_E_DECAY) * _E_DECAY * (_Q - _E_DECAY) ** 2, _E_DECAY)
_U = np.linspace(0.0, 1.0, 1500)     # variable de integración reescalada


def weak_rates(T: float, T_nu: float, tau_n: float) -> tuple[float, float]:
    """(λ n→p, λ p→n) en 1/s a temperatura de fotones T y de neutrinos T_ν (MeV)."""
    K = 1.0 / (tau_n * _DECAY_PHASE_SPACE)
    upper = 30 * max(T, T_nu) + _Q + _ME      # más allá, las distribuciones son ~0

    # n + ν → p + e⁻   (integramos en la energía del neutrino)
    ev = _U * upper
    ee = ev + _Q
    r1 = np.trapezoid(ev**2 * _p(ee) * ee * _fermi(ev, T_nu) * (1 - _fermi(ee, T)), ev)
    # n + e⁺ → p + ν̄   (integramos en la energía del positrón)
    ee = _ME + _U * upper
    ev = ee + _Q
    r2 = np.trapezoid(_p(ee) * ee * ev**2 * _fermi(ee, T) * (1 - _fermi(ev, T_nu)), ee)
    # n → p + e⁻ + ν̄   (con bloqueo de Pauli del medio)
    ee = _E_DECAY
    ev = _Q - ee
    r3 = np.trapezoid(_p(ee) * ee * ev**2 * (1 - _fermi(ee, T)) * (1 - _fermi(ev, T_nu)), ee)

    # p + e⁻ → n + ν   (el electrón necesita E > Q)
    ee = _Q + _U * upper
    ev = ee - _Q
    r4 = np.trapezoid(_p(ee) * ee * ev**2 * _fermi(ee, T) * (1 - _fermi(ev, T_nu)), ee)
    # p + ν̄ → n + e⁺   (el antineutrino necesita E > Q + m_e)
    ev = _Q + _ME + _U * upper
    ee = ev - _Q
    r5 = np.trapezoid(ev**2 * _p(ee) * ee * _fermi(ev, T_nu) * (1 - _fermi(ee, T)), ev)

    return K * (r1 + r2 + r3), K * (r4 + r5)


# --- Resultado ------------------------------------------------------------------

@dataclass(frozen=True)
class Epoch:
    """Un momento destacado de la historia, para la cronología."""
    key: str
    title: str
    description: str
    time_s: float
    temperature_mev: float
    neutron_fraction: float

    @property
    def temperature_k(self) -> float:
        return self.temperature_mev * MEV_TO_KELVIN


@dataclass
class NucleosynthesisResult:
    baryon_to_photon: float
    neutron_lifetime_s: float
    neutrino_families: float
    history: ThermalHistory
    neutron_fraction: np.ndarray        # X_n = n/(n+p) en cada instante
    helium_mass_fraction: float         # Y_p
    nucleosynthesis_time_s: float
    nucleosynthesis_temperature_mev: float
    epochs: list[Epoch] = field(default_factory=list)

    @property
    def hydrogen_mass_fraction(self) -> float:
        return 1 - self.helium_mass_fraction

    @property
    def neutron_to_proton_at_freezeout(self) -> float:
        e = next(e for e in self.epochs if e.key == "freezeout")
        return e.neutron_fraction / (1 - e.neutron_fraction)

    @property
    def helium_atoms_per_hydrogen(self) -> float:
        """Núcleos de helio por cada núcleo de hidrógeno (un He pesa ~4 H)."""
        y = self.helium_mass_fraction
        return (y / 4) / (1 - y)

    def at_time(self, t: float) -> tuple[float, float]:
        """(temperatura en MeV, X_n) en el instante t (s), interpolando."""
        h = self.history
        temp = float(np.exp(np.interp(np.log(t), np.log(h.time), np.log(h.temperature))))
        xn = float(np.interp(np.log(t), np.log(h.time), self.neutron_fraction))
        return temp, xn


# --- Simulación -----------------------------------------------------------------

def deuterium_saha_ratio(T: np.ndarray, eta: float) -> np.ndarray:
    """X_D / (X_n·X_p) en equilibrio (ecuación de Saha).

    Cuando vale ~1 el deuterio deja de romperse: el cuello de botella se abre.
    El factor η hace que esto ocurra a T ≈ 0.07 MeV y no a 2.2 MeV (su energía
    de enlace): hay tantos fotones por barión que basta una fracción minúscula
    de fotones energéticos para destruirlo.
    """
    # g_D · ζ(3) · π^(-1/2) · 2^(1/2) · 2^(5/2) ≈ 16.3   (Kolb & Turner, ec. 4.17)
    prefactor = 3 * _ZETA3 / np.sqrt(np.pi) * 2 ** 0.5 * 2 ** 2.5
    return prefactor * eta * (T / NUCLEON_MASS_MEV) ** 1.5 * np.exp(DEUTERON_BINDING_MEV / T)


def simulate(baryon_to_photon: float = BARYON_TO_PHOTON,
             neutron_lifetime_s: float = NEUTRON_LIFETIME_S,
             neutrino_families: float = NEUTRINO_FAMILIES) -> NucleosynthesisResult:
    if not 1e-12 <= baryon_to_photon <= 1e-6:
        raise ValueError("The baryon-to-photon ratio must be between 1e-12 and 1e-6.")
    if not 100 <= neutron_lifetime_s <= 5000:
        raise ValueError("The neutron lifetime must be between 100 and 5000 s.")
    if not 0 <= neutrino_families <= 10:
        raise ValueError("The number of neutrino families must be between 0 and 10.")

    h = thermal_history(neutrino_families)
    T, t = h.temperature, h.time
    rates = np.array([weak_rates(a, b, neutron_lifetime_s)
                      for a, b in zip(T, h.neutrino_temperature)])
    lam_np, lam_pn = rates[:, 0], rates[:, 1]

    # Euler implícito: estable aunque las tasas sean enormes a alta temperatura.
    xn = np.empty_like(T)
    xn[0] = 1 / (1 + np.exp(NEUTRON_PROTON_DIFF_MEV / T[0]))   # equilibrio inicial
    for k in range(len(T) - 1):
        dt = t[k + 1] - t[k]
        xn[k + 1] = (xn[k] + dt * lam_pn[k + 1]) / (1 + dt * (lam_np[k + 1] + lam_pn[k + 1]))

    # Fin del cuello de botella: primer instante en que la Saha del deuterio alcanza ~1
    saha = deuterium_saha_ratio(T, baryon_to_photon) * (1 - xn)
    k_nuc = int(np.argmax(saha >= 1))
    if saha[k_nuc] < 1:
        k_nuc = len(T) - 1
    helium = 2 * xn[k_nuc]          # cada He-4 lleva 2 neutrones: Y = 2·X_n

    # Tras la nucleosíntesis los neutrones están dentro del helio: X_n queda fijo.
    xn_free = xn.copy()
    xn[k_nuc:] = xn[k_nuc]

    epochs = _epochs(h, xn_free, lam_np + lam_pn, k_nuc, helium)
    return NucleosynthesisResult(baryon_to_photon, neutron_lifetime_s, neutrino_families,
                                 h, xn, float(helium), float(t[k_nuc]), float(T[k_nuc]), epochs)


def _epochs(h: ThermalHistory, xn: np.ndarray, weak_rate: np.ndarray,
            k_nuc: int, helium: float) -> list[Epoch]:
    T, t = h.temperature, h.time

    def make(key, k, title, description):
        return Epoch(key, title, description, float(t[k]), float(T[k]), float(xn[k]))

    k_freeze = int(np.argmax(weak_rate < h.hubble))
    ratio_heat = T / h.neutrino_temperature
    k_annihilation = int(np.argmax(ratio_heat > 1 + 0.5 * ((11 / 4) ** (1 / 3) - 1)))

    n_over_p = xn[k_freeze] / (1 - xn[k_freeze])
    return [
        make("equilibrium", 0, "Thermal equilibrium",
             "A hot soup of photons, electrons, positrons and neutrinos. Weak reactions "
             "turn neutrons into protons and back so fast that n/p = e^(-Q/T)."),
        make("freezeout", k_freeze, "Weak freeze-out",
             "The universe expands faster than the weak reactions can act: the "
             f"neutron-to-proton ratio freezes at about 1/{1 / n_over_p:.1f}."),
        make("annihilation", k_annihilation, "Electron-positron annihilation",
             "Electrons and positrons annihilate and heat the photons, but not the "
             "already decoupled neutrinos. Today T_nu/T_gamma = (4/11)^(1/3)."),
        make("nucleosynthesis", k_nuc, "The deuterium bottleneck opens",
             "Deuterium now survives the photons. Almost every remaining neutron ends "
             f"up inside helium-4: Y = 2*X_n = {helium:.3f}."),
    ]
