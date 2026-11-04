"""Nucleosíntesis primordial: los tres primeros minutos.

Simula cómo se fabricó el helio del universo, siguiendo el relato de Steven Weinberg:

  1. Universo muy caliente (T > 10¹⁰ K): neutrones y protones se transforman unos en otros
     sin parar (n + ν ⇄ p + e⁻, n + e⁺ ⇄ p + ν̄). Hay casi tantos neutrones como protones.
  2. Al enfriarse, estas reacciones débiles se vuelven más lentas que la expansión y la
     proporción n/p se "congela" en ~1/6 (T ≈ 0.8 MeV ≈ 10¹⁰ K, t ≈ 1 s).
  3. Los neutrones libres se desintegran (vida media ~15 min) mientras esperan.
  4. Cuello de botella del deuterio: el deuterio (n + p) se forma, pero los fotones lo
     rompen en cuanto aparece, porque hay ~1600 millones de fotones por cada nucleón.
  5. Cuando el universo se enfría a ~10⁹ K (t ≈ 3 minutos) el deuterio por fin sobrevive
     y casi todos los neutrones restantes acaban en helio-4.
     Resultado: ~25 % de la masa en helio, ~75 % en hidrógeno. ¡Es lo que se observa!

MODELO (simplificado pero físico; ver referencias al final):
  - Expansión: universo dominado por radiación (fotones, e±, neutrinos). La aniquilación
    e⁺e⁻ se trata con conservación de entropía, así que el calentamiento de los fotones
    respecto a los neutrinos (T_ν/T = (4/11)^⅓ al final) sale solo.
  - Tasas débiles n ⇄ p: aproximación analítica de Mukhanov (2004).
  - Desintegración libre del neutrón con su vida media medida.
  - Mini red nuclear de 3 especies:
        n + p ⇄ D + γ       muy rápida: el deuterio sigue el equilibrio de Saha
        D + D → ⁴He         reacción efectiva (en realidad pasa por ³He y ³H)
    El helio se va formando poco a poco, no de golpe, y la simulación da además una
    estimación del deuterio que sobrevive.
  - No se calculan ³He ni ⁷Li: para eso hace falta una red completa (PRIMAT, PArthENoPE...).

Precisión: Y_p con un error de ~0.01 respecto a los códigos completos; el deuterio
residual solo en orden de magnitud. Suficiente para ver las tendencias:
más neutrinos → más helio; más bariones → más helio y menos deuterio.

Como el resto del núcleo, este módulo no imprime nada: devuelve datos.
"""
import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

# --- Constantes físicas (unidades: MeV, segundos) -------------------------------
Q_MEV = 1.29333236             # m_n - m_p (CODATA 2018)
ELECTRON_MASS_MEV = 0.51099895
NUCLEON_MASS_MEV = 938.918     # media de protón y neutrón
DEUTERON_BINDING_MEV = 2.224566
PLANCK_MASS_MEV = 1.220890e22  # masa de Planck, √(ħc/G)
HBAR_MEV_S = 6.582119569e-22   # ħ, para pasar de MeV a s⁻¹
ZETA3 = 1.2020569
MEV_TO_KELVIN = 1.160451812e10

# --- Parámetros por defecto (valores medidos) ---------------------------------
DEFAULT_ETA = 6.1e-10          # bariones por fotón (Planck 2018: Ω_b h² = 0.0224)
DEFAULT_NEUTRON_LIFETIME_S = 878.4   # PDG 2024
DEFAULT_NEUTRINO_SPECIES = 3.0

# Valores de referencia para comparar (PDG 2024, revisión "Big-Bang Nucleosynthesis")
OBSERVED_HELIUM = 0.245        # Y_p observado en galaxias pobres en metales (±0.003)
STANDARD_BBN_HELIUM = 0.247    # predicción de los códigos completos con el η de Planck
OBSERVED_D_TO_H = 2.55e-5      # D/H observado en nubes de gas lejanas (±0.03e-5)

# Los "fotogramas" de Weinberg en "Los tres primeros minutos" (temperaturas en kelvin)
WEINBERG_FRAMES_K = {
    "First frame": 1e11,
    "Second frame": 3e10,
    "Third frame": 1e10,
    "Fourth frame": 3e9,
    "Fifth frame": 1e9,
    "Sixth frame": 3e8,
}


def kelvin(t_mev: float) -> float:
    return t_mev * MEV_TO_KELVIN


# --- Termodinámica de electrones y positrones --------------------------------------
# f_rho y f_s valen 1 cuando los e± son ultrarrelativistas (T ≫ m_e) y 0 cuando ya se
# han aniquilado (T ≪ m_e). Son integrales de Fermi-Dirac normalizadas.

def _simpson(f, a: float, b: float, n: int = 200) -> float:
    h = (b - a) / n
    s = f(a) + f(b)
    s += 4 * sum(f(a + i * h) for i in range(1, n, 2))
    s += 2 * sum(f(a + i * h) for i in range(2, n, 2))
    return s * h / 3


@lru_cache(maxsize=None)
def _electron_factors(z: float) -> tuple[float, float]:
    """(f_rho, f_s) para z = m_e / T."""
    def fermi(e):
        return 1.0 / (math.exp(e) + 1.0) if e < 700 else 0.0

    def rho(x):
        e = math.sqrt(x * x + z * z)
        return x * x * e * fermi(e)

    def entropy(x):          # (ρ + P) / T
        e = math.sqrt(x * x + z * z)
        return (x * x * e + x ** 4 / (3 * e)) * fermi(e) if e > 0 else 0.0

    upper = 40.0 + z
    rho_rel = 7 * math.pi ** 4 / 120
    return _simpson(rho, 0, upper) / rho_rel, _simpson(entropy, 0, upper) / (4 / 3 * rho_rel)


def electron_factors(t_mev: float) -> tuple[float, float]:
    z = ELECTRON_MASS_MEV / t_mev
    if z > 60:
        return 0.0, 0.0
    return _electron_factors(round(z, 3))   # redondeo para aprovechar la caché


def neutrino_temperature_ratio(t_mev: float) -> float:
    """T_ν / T. Vale 1 antes de la aniquilación e± y (4/11)^⅓ ≈ 0.714 después.

    Los e± al aniquilarse dan su entropía a los fotones, no a los neutrinos (que ya
    se habían desacoplado): por eso los fotones quedan más calientes.
    """
    _f_rho, f_s = electron_factors(t_mev)
    g_s = 2 + 7 / 8 * 4 * f_s           # fotones + e±
    return (g_s / (11 / 2)) ** (1 / 3)


def hubble_rate(t_mev: float, neutrino_species: float) -> float:
    """Ritmo de expansión H en s⁻¹ (Friedmann con densidad de radiación)."""
    f_rho, _f_s = electron_factors(t_mev)
    r = neutrino_temperature_ratio(t_mev)
    g_rho = 2 + 7 / 8 * 4 * f_rho + 7 / 8 * 2 * neutrino_species * r ** 4
    rho = math.pi ** 2 / 30 * g_rho * t_mev ** 4                       # MeV⁴
    h_mev = math.sqrt(8 * math.pi * rho / 3) / PLANCK_MASS_MEV         # MeV
    return h_mev / HBAR_MEV_S


# --- Física nuclear ----------------------------------------------------------

def weak_rate(t_nu_mev: float) -> float:
    """Tasa n → p por interacciones débiles con e± y ν (s⁻¹). Mukhanov (2004):
    λ ≈ 2 · 1.63 · y³ (y + 0.25)²  con  y = T_ν / Q."""
    y = t_nu_mev / Q_MEV
    return 2 * 1.63 * y ** 3 * (y + 0.25) ** 2


def equilibrium_neutron_fraction(t_mev: float) -> float:
    """n / (n + p) en equilibrio: n/p = e^(−Q/T)."""
    return 1.0 / (1.0 + math.exp(min(Q_MEV / t_mev, 700)))


def saha_deuterium(t_mev: float, eta: float, xn: float) -> float:
    """Fracción de masa de deuterio en equilibrio de Saha con neutrones y protones.

    X_D = (3/2)·(2ζ(3)/π²)·(4π)^{3/2} · η · (T/m_N)^{3/2} · e^{B_D/T} · X_n X_p
        ≈ 16.3 · η · (T/m_N)^{3/2} · e^{B_D/T} · X_n X_p
    El factor η (bariones/fotón ≈ 6·10⁻¹⁰) es tan pequeño que hace falta que e^{B/T} sea
    enorme (T ≪ B_D) para que haya deuterio: ese es el "cuello de botella".
    """
    coefficient = 1.5 * (2 * ZETA3 / math.pi ** 2) * (4 * math.pi) ** 1.5
    exponent = min(DEUTERON_BINDING_MEV / t_mev, 700)
    return coefficient * eta * (t_mev / NUCLEON_MASS_MEV) ** 1.5 * math.exp(exponent) * xn * (1 - xn)


HBAR_C_MEV_CM = 1.973269804e-11   # ħc en MeV·cm, para pasar T³ a partículas/cm³


def baryon_density(t_mev: float, eta: float) -> float:
    """Bariones por cm³: n_b = η · n_γ, con n_γ = (2ζ(3)/π²) T³."""
    return eta * 2 * ZETA3 / math.pi ** 2 * (t_mev / HBAR_C_MEV_CM) ** 3


def rate_np_to_d(t_mev: float) -> float:
    """⟨σv⟩ de n + p → D + γ en cm³/s (ajuste de Ando et al. 2006). Casi constante, ~4.4e-20."""
    t9 = kelvin(t_mev) / 1e9
    num = 1 + 3.75 * t9 + 1.93 * t9 ** 2 + 0.747 * t9 ** 3 + 0.0197 * t9 ** 4 + 3.00491e-6 * t9 ** 5
    den = 1 + 5.47 * t9 + 5.62 * t9 ** 2 + 0.489 * t9 ** 3 + 7.47e-3 * t9 ** 4
    return 4.42e4 * num / den / 6.02214076e23


def rate_dd(t_mev: float) -> float:
    """⟨σv⟩ total de D + D (→ ³He + n y → ³H + p) en cm³/s.

    Forma de Gamow (dos cargas que deben atravesar su repulsión eléctrica por efecto
    túnel), normalizada a 3.3e-17 cm³/s a T = 0.075 MeV (valores de Mukhanov 2004).
    """
    t9 = kelvin(t_mev) / 1e9
    t9_ref = kelvin(0.075) / 1e9

    def shape(x):
        return x ** (-2 / 3) * math.exp(-4.2487 * x ** (-1 / 3))

    return 3.3e-17 * shape(t9) / shape(t9_ref)


# --- Simulación ----------------------------------------------------------------

@dataclass(frozen=True)
class Snapshot:
    time_s: float
    temperature_mev: float
    neutron_fraction: float          # X_n: fracción de masa en neutrones libres
    deuterium_fraction: float        # X_D: fracción de masa en deuterio
    helium_fraction: float           # Y:   fracción de masa en helio-4
    equilibrium_fraction: float      # X_n si las reacciones débiles fueran instantáneas

    @property
    def temperature_k(self) -> float:
        return kelvin(self.temperature_mev)

    @property
    def proton_fraction(self) -> float:
        return 1 - self.neutron_fraction - self.deuterium_fraction - self.helium_fraction

    @property
    def neutron_to_proton(self) -> float:
        """n/p contando solo nucleones libres."""
        return self.neutron_fraction / self.proton_fraction

    @property
    def deuterium_to_hydrogen(self) -> float:
        """D/H en número de núcleos (lo que miden los astrónomos)."""
        return (self.deuterium_fraction / 2) / self.proton_fraction


@dataclass(frozen=True)
class Event:
    name: str
    description: str
    snapshot: Snapshot


@dataclass
class NucleosynthesisResult:
    eta: float
    neutron_lifetime_s: float
    neutrino_species: float
    history: list[Snapshot] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    @property
    def final(self) -> Snapshot:
        return self.history[-1]

    @property
    def helium_fraction(self) -> float:
        """Y_p: fracción de masa de helio-4 primordial."""
        return self.final.helium_fraction

    @property
    def hydrogen_fraction(self) -> float:
        return self.final.proton_fraction

    @property
    def deuterium_to_hydrogen(self) -> float:
        return self.final.deuterium_to_hydrogen

    def event(self, name: str) -> Event:
        return next(e for e in self.events if e.name == name)

    def at_temperature(self, t_mev: float) -> Snapshot:
        """Instantánea más cercana a una temperatura dada."""
        return min(self.history, key=lambda s: abs(math.log(s.temperature_mev / t_mev)))


def simulate(eta: float = DEFAULT_ETA,
             neutron_lifetime_s: float = DEFAULT_NEUTRON_LIFETIME_S,
             neutrino_species: float = DEFAULT_NEUTRINO_SPECIES,
             t_start_mev: float = 20.0, t_end_mev: float = 0.01,
             steps: int = 3000) -> NucleosynthesisResult:
    """Simula la nucleosíntesis desde T = 20 MeV (t ≈ 2 ms) hasta T = 0.01 MeV (~3.5 h)."""
    if not 1e-12 < eta < 1e-7:
        raise ValueError("eta must be between 1e-12 and 1e-7 (measured: 6.1e-10).")
    if neutron_lifetime_s <= 0:
        raise ValueError("The neutron lifetime must be positive.")
    if not 0 <= neutrino_species <= 10:
        raise ValueError("The number of neutrino species must be between 0 and 10.")

    result = NucleosynthesisResult(eta, neutron_lifetime_s, neutrino_species)
    ratio = math.exp(math.log(t_end_mev / t_start_mev) / steps)   # paso logarítmico en T

    temp = t_start_mev
    t = 1 / (2 * hubble_rate(temp, neutrino_species))   # universo de radiación: t = 1/(2H)
    # "unburned": neutrones que aún no están en helio (libres + dentro del deuterio)
    unburned = equilibrium_neutron_fraction(temp)
    helium = 0.0
    xn, xd = unburned, 0.0

    def snap() -> Snapshot:
        return Snapshot(t, temp, xn, xd, helium, equilibrium_neutron_fraction(temp))

    def split(n_total: float, t_mev: float) -> tuple[float, float]:
        """Reparte los neutrones sin quemar entre libres y deuterio según Saha:
        X_D = S·X_n·X_p  con  X_n + X_D/2 = n_total."""
        xp = max(1 - helium - n_total - xd / 2, 1e-30)      # protones libres (aprox.)
        s_xp = saha_deuterium(t_mev, eta, 0.5) * 4 * xp     # S·X_p  (saha(…,0.5) = S/4)
        g = (s_xp / 2) / (1 + s_xp / 2)                      # fracción en deuterio
        return n_total * (1 - g), 2 * n_total * g

    result.history.append(snap())
    frozen = False
    for _ in range(steps):
        new_temp = temp * ratio
        # Tiempo transcurrido: d ln a = −d ln T_ν (los neutrinos se enfrían como 1/a)
        tnu_old = temp * neutrino_temperature_ratio(temp)
        tnu_new = new_temp * neutrino_temperature_ratio(new_temp)
        h_mid = hubble_rate(math.sqrt(temp * new_temp), neutrino_species)
        dt = math.log(tnu_old / tnu_new) / h_mid
        temp, t = new_temp, t + dt

        # 1) Reacciones débiles y desintegración, solo sobre neutrones LIBRES (Euler implícito)
        free_share = xn / unburned if unburned > 0 else 1.0
        lam = weak_rate(tnu_new) * (1 + math.exp(-Q_MEV / temp))
        x_eq = equilibrium_neutron_fraction(temp) * (1 - helium)
        unburned = (unburned + dt * lam * x_eq) / (1 + dt * (lam + 1 / neutron_lifetime_s) * free_share)

        # 2) Deuterio en equilibrio con n y p
        xn, xd = split(unburned, temp)

        # 3) D + D → ⁴He. dY/dt = ½⟨σv⟩ n_b X_D². Con X_D = 2g·N, la ecuación
        #    dN/dt = −k N² se resuelve exacta en el paso: N ← N / (1 + k N dt)
        if xd > 0:
            g = xd / (2 * unburned)
            k = rate_dd(temp) * baryon_density(temp, eta) * g * g
            burned_from = unburned
            unburned = unburned / (1 + k * unburned * dt)
            helium += 2 * (burned_from - unburned)
            xn, xd = split(unburned, temp)

        if not frozen and lam < h_mid:
            frozen = True
            result.events.append(Event(
                "freeze_out", "Weak interactions freeze out: n/p stops following equilibrium",
                snap()))
        result.history.append(snap())

    _add_events(result)
    return result


def _add_events(result: NucleosynthesisResult) -> None:
    """Momentos clave, deducidos de la historia ya calculada."""
    hist = result.history
    peak = max(hist, key=lambda s: s.deuterium_fraction)
    half = next(s for s in hist if s.helium_fraction >= result.helium_fraction / 2)
    annihilation = next(s for s in hist if neutrino_temperature_ratio(s.temperature_mev) < 0.85)
    result.events += [
        Event("annihilation", "Electrons and positrons annihilate, heating the photons", annihilation),
        Event("nucleosynthesis", "The deuterium bottleneck breaks: half the helium is made", half),
        Event("deuterium_peak", "Deuterium reaches its maximum abundance", peak),
    ]
    result.events.sort(key=lambda e: e.snapshot.time_s)


def timeline(result: NucleosynthesisResult) -> list[tuple[str, str, Snapshot]]:
    """Fotogramas de Weinberg + momentos clave, ordenados en el tiempo.

    Devuelve (título, descripción, instantánea).
    """
    rows = [(name, "", result.at_temperature(k / MEV_TO_KELVIN))
            for name, k in WEINBERG_FRAMES_K.items()]
    rows += [(e.name.replace("_", " ").capitalize(), e.description, e.snapshot)
             for e in result.events if e.name != "deuterium_peak"]
    return sorted(rows, key=lambda r: r[2].time_s)


# --- Modo "partícula a partícula" ----------------------------------------------------

def _binomial(n: int, p: float, rng: random.Random) -> int:
    if n <= 0 or p <= 0:
        return 0
    if p >= 1:
        return n
    if hasattr(rng, "binomialvariate"):            # Python ≥ 3.12
        return rng.binomialvariate(n, p)
    variance = n * p * (1 - p)
    if variance > 25:                              # aproximación normal: rápida y precisa aquí
        return min(n, max(0, round(rng.gauss(n * p, math.sqrt(variance)))))
    return sum(rng.random() < p for _ in range(n))


@dataclass(frozen=True)
class ParticleCount:
    time_s: float
    temperature_mev: float
    neutrons: int
    protons: int
    helium_nuclei: int

    @property
    def total(self) -> int:
        return self.neutrons + self.protons + 4 * self.helium_nuclei

    @property
    def helium_fraction(self) -> float:
        return 4 * self.helium_nuclei / self.total


def simulate_particles(n_nucleons: int = 1000, eta: float = DEFAULT_ETA,
                       neutron_lifetime_s: float = DEFAULT_NEUTRON_LIFETIME_S,
                       neutrino_species: float = DEFAULT_NEUTRINO_SPECIES,
                       rng: random.Random | None = None,
                       steps: int = 600) -> list[ParticleCount]:
    """Lo mismo, pero con N nucleones individuales que cambian al azar.

    En cada paso, cada neutrón tiene una probabilidad de convertirse en protón (y al revés)
    y de acabar en helio, calculadas con las mismas tasas físicas que la simulación exacta.
    Con pocos nucleones el resultado fluctúa; con muchos se acerca a la simulación exacta.
    Es el "Big Bang" aleatorio del programa original, pero ahora con física.
    """
    if n_nucleons < 4:
        raise ValueError("At least 4 nucleons are needed to make a helium nucleus.")
    rng = rng or random.Random()
    ref = simulate(eta, neutron_lifetime_s, neutrino_species, steps=steps)

    first = ref.history[0]
    neutrons = round(n_nucleons * first.neutron_fraction)
    protons = n_nucleons - neutrons
    helium = 0
    counts = [ParticleCount(first.time_s, first.temperature_mev, neutrons, protons, 0)]

    for prev, cur in zip(ref.history, ref.history[1:]):
        dt = cur.time_s - prev.time_s
        tnu = cur.temperature_mev * neutrino_temperature_ratio(cur.temperature_mev)
        lam = weak_rate(tnu)
        p_np = 1 - math.exp(-(lam + 1 / neutron_lifetime_s) * dt)
        p_pn = 1 - math.exp(-lam * math.exp(-Q_MEV / cur.temperature_mev) * dt)
        n_to_p = _binomial(neutrons, p_np, rng)
        p_to_n = _binomial(protons, p_pn, rng)
        neutrons += p_to_n - n_to_p
        protons += n_to_p - p_to_n

        # Probabilidad de que un neutrón sin quemar acabe en helio en este paso,
        # tomada de la simulación exacta (lo que se "quemó" en ese mismo paso).
        unburned_prev = prev.neutron_fraction + prev.deuterium_fraction / 2
        unburned_cur = cur.neutron_fraction + cur.deuterium_fraction / 2
        burned = (prev.helium_fraction < cur.helium_fraction) and unburned_prev > 0
        if burned:
            p_burn = min(1.0, (cur.helium_fraction - prev.helium_fraction) / 2 / unburned_prev)
            pairs = min(_binomial(neutrons, p_burn, rng), protons) // 2   # 2n + 2p → ⁴He
            if unburned_cur < 1e-3 and neutrons >= 2:
                pairs = max(pairs, min(neutrons, protons) // 2)          # fin: barrer los que quedan
            helium += pairs
            neutrons -= 2 * pairs
            protons -= 2 * pairs
        counts.append(ParticleCount(cur.time_s, cur.temperature_mev, neutrons, protons, helium))
    return counts


# Referencias:
#  - S. Weinberg, "The First Three Minutes" (1977).
#  - V. Mukhanov, "Nucleosynthesis without a computer", Int. J. Theor. Phys. 43, 669 (2004),
#    arXiv:astro-ph/0303073.
#  - S. Ando et al., Phys. Rev. C 74, 025809 (2006): ritmo de n + p → D + γ.
#  - E. W. Kolb & M. S. Turner, "The Early Universe" (1990), cap. 4.
#  - Particle Data Group, Review of Particle Physics (2024): vida media del neutrón,
#    revisión "Big-Bang Nucleosynthesis".
