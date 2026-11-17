"""Nucleosíntesis primordial: los tres primeros minutos.

Simula cómo se fabricaron los primeros núcleos del universo, siguiendo el relato de Steven
Weinberg:

  1. Universo muy caliente (T > 10¹⁰ K): neutrones y protones se transforman unos en otros
     sin parar (n + ν ⇄ p + e⁻, n + e⁺ ⇄ p + ν̄). Hay casi tantos neutrones como protones.
  2. Al enfriarse, estas reacciones débiles se vuelven más lentas que la expansión y la
     proporción n/p se "congela" en ~1/6 (T ≈ 0.8 MeV ≈ 10¹⁰ K, t ≈ 1 s).
  3. Los neutrones libres se desintegran (vida media ~15 min) mientras esperan.
  4. Cuello de botella del deuterio: el deuterio (n + p) se forma, pero los fotones lo
     rompen en cuanto aparece, porque hay ~1600 millones de fotones por cada nucleón.
  5. Cuando el universo se enfría a ~10⁹ K (t ≈ 3 minutos) el deuterio por fin sobrevive
     y casi todos los neutrones restantes acaban en helio-4. Queda un poco de deuterio,
     helio-3 y litio-7.
     Resultado: ~25 % de la masa en helio, ~75 % en hidrógeno. ¡Es lo que se observa!

MODELO (ver docs/TECNICO.md y las referencias al final):
  - Expansión: universo dominado por radiación (fotones, e±, neutrinos). La aniquilación
    e⁺e⁻ se trata con conservación de entropía, así que el calentamiento de los fotones
    respecto a los neutrinos (T_ν/T = (4/11)^⅓ al final) sale solo.
  - Tasas débiles n ⇄ p: integrales de Born completas (las seis reacciones, con las
    distribuciones de Fermi-Dirac de e± y neutrinos), normalizadas con la vida media medida.
  - Red nuclear de 8 núcleos (n, p, D, T, ³He, ⁴He, ⁷Li, ⁷Be) y 18 reacciones, con las tasas
    medidas de nuclear_rates.py; las inversas, por balance detallado.
  - Integración implícita (BDF2 con Newton), porque las reacciones con fotones son miles de
    millones de veces más rápidas que la expansión.

Precisión frente a los códigos completos (PRIMAT, PArthENoPE, AlterBBN): Y_p a ~0.001 y D/H,
³He/H y ⁷Li/H a unos pocos %. Lo que falta: correcciones radiativas y de temperatura finita a
las tasas débiles, y núcleos más pesados (⁶Li, ⁹Be, B...) que no cambian estos resultados.

Como el resto del núcleo, este módulo no imprime nada: devuelve datos.
"""
import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from . import nuclear_rates as nr

# --- Constantes físicas (unidades: MeV, segundos) -------------------------------
Q_MEV = 1.29333251             # m_n − m_p (CODATA 2022)
ELECTRON_MASS_MEV = 0.51099895
NUCLEON_MASS_MEV = 938.918     # media de protón y neutrón
DEUTERON_BINDING_MEV = 2.224566
PLANCK_MASS_MEV = 1.220890e22  # masa de Planck, √(ħc/G)
HBAR_MEV_S = 6.582119569e-22   # ħ, para pasar de MeV a s⁻¹
HBAR_C_MEV_CM = 1.973269804e-11   # ħc en MeV·cm, para pasar T³ a partículas/cm³
ATOMIC_MASS_UNIT_G = 1.66053907e-24
ZETA3 = 1.2020569
MEV_TO_KELVIN = 1.160451812e10

# --- Parámetros por defecto (valores medidos) ---------------------------------
DEFAULT_ETA = 6.1e-10          # bariones por fotón hoy (Planck 2018: Ω_b h² = 0.0224)
DEFAULT_NEUTRON_LIFETIME_S = 878.4   # PDG 2024
DEFAULT_NEUTRINO_SPECIES = 3.0

# Observaciones (PDG 2026, revisión "Big-Bang Nucleosynthesis" de B. Fields, P. Molaro y
# S. Sarkar, agosto de 2025)
OBSERVED_HELIUM = 0.245        # Y_p en galaxias pobres en metales (±0.003)
OBSERVED_D_TO_H = 2.508e-5     # D/H en nubes de gas lejanas (±0.029e-5)
OBSERVED_LI7_TO_H = 1.45e-10   # ⁷Li/H en estrellas viejas del halo (±0.25e-10)
# El ³He primordial no se ha podido medir: solo hay datos del Sistema Solar y de la Galaxia.

# Predicción de los códigos completos con el η de Planck (Fields et al., JCAP 03, 010, 2020)
STANDARD_BBN_HELIUM = 0.247    # 0.24691 ± 0.00018
STANDARD_BBN_D_TO_H = 2.57e-5  # ± 0.13e-5
STANDARD_BBN_HE3_TO_H = 1.003e-5   # ± 0.090e-5
STANDARD_BBN_LI7_TO_H = 4.72e-10   # ± 0.72e-10: 3 veces lo observado, el "problema del litio"

# Correcciones a las tasas débiles que la aproximación de Born no incluye (radiativas, con la
# de Coulomb, y masa finita de los nucleones): suben Y_p en 44·10⁻⁴, un 1,8 % (Pitrou et al.,
# Phys. Rep. 754, 1, 2018; tabla 2 de arXiv:1909.12046). Se aplican al resultado final.
WEAK_CORRECTION_HELIUM = 1.018

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


def entropy_degrees(t_mev: float) -> float:
    """Grados de libertad de la entropía de fotones + e± (2 tras la aniquilación, 11/2 antes)."""
    _f_rho, f_s = electron_factors(t_mev)
    return 2 + 7 / 8 * 4 * f_s


# --- Física nuclear ----------------------------------------------------------

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


def baryon_density(t_mev: float, eta: float) -> float:
    """Bariones por cm³: n_b = η · n_γ · g_s/2, con n_γ = (2ζ(3)/π²) T³.

    η es la proporción de HOY. Antes de la aniquilación e± había menos fotones por barión
    (los e± todavía no les habían dado su entropía): el factor g_s/2 lo tiene en cuenta.
    """
    return eta * entropy_degrees(t_mev) / 2 * 2 * ZETA3 / math.pi ** 2 * (t_mev / HBAR_C_MEV_CM) ** 3


def rate_np_to_d(t_mev: float) -> float:
    """⟨σv⟩ de n + p → D + γ en cm³/s (ajuste de Ando et al. 2006). Casi constante, ~4.4e-20."""
    return nr.rate_n_p(kelvin(t_mev) / 1e9) / 6.02214076e23


# --- Tasas débiles n ⇄ p (aproximación de Born) ------------------------------------
# En unidades de la masa del electrón, con ε la energía del e± y q = Q/m_e:
#   λ(n→p) = 1/(τ·λ₀) ∫ ε·p [ (ε−q)²·(1−f_e(ε))·f_ν(ε−q)…  +  (ε+q)²·f_e(ε)·(1−f_ν(ε+q)) ] dε
# El primer término reúne n + ν → p + e⁻ (ε > q) y la desintegración n → p + e⁻ + ν̄ (ε < q);
# el segundo, n + e⁺ → p + ν̄. λ(p→n) es lo mismo con q → −q. λ₀ = ∫₁^q ε·p·(q−ε)² dε normaliza
# con la vida media medida: a T = 0 queda λ(n→p) = 1/τ. (Weinberg 1972; Bernstein, Brown y
# Feinberg, Rev. Mod. Phys. 61, 25, 1989.) Las integrales se hacen en p (ε dε = p dp).

_Q_ME = Q_MEV / ELECTRON_MASS_MEV


def _fermi(x: float) -> float:
    """1 / (eˣ + 1), sin desbordarse."""
    if x > 700:
        return 0.0
    if x < -700:
        return 1.0
    return 1.0 / (math.exp(x) + 1.0)


def _simpson_sum(f, a: float, b: float, n: int) -> float:
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(a + i * h)
    return total * h / 3


def _born_integrals(z: float, z_nu: float) -> tuple[float, float]:
    """(I n→p, I p→n), adimensionales, con z = m_e/T y z_ν = m_e/T_ν."""
    q = _Q_ME

    def n_to_p(p: float) -> float:
        e = math.sqrt(1 + p * p)
        fe = _fermi(e * z)
        return p * p * ((e - q) ** 2 * (1 - fe) * _fermi((e - q) * z_nu)       # n+ν→p+e⁻, n→p+e⁻+ν̄
                        + (e + q) ** 2 * fe * _fermi(-(e + q) * z_nu))         # n+e⁺→p+ν̄

    def p_to_n(p: float) -> float:
        e = math.sqrt(1 + p * p)
        fe = _fermi(e * z)
        return p * p * ((e + q) ** 2 * (1 - fe) * _fermi((e + q) * z_nu)       # p+ν̄→n+e⁺
                        + (e - q) ** 2 * fe * _fermi(-(e - q) * z_nu))         # p+e⁻→n+ν

    p_q = math.sqrt(q * q - 1)                       # el electrón de la desintegración, a lo sumo
    e_max = q + 60.0 / min(z, z_nu) + 2.0            # más allá, las ocupaciones son ~0
    p_max = math.sqrt(e_max * e_max - 1)
    return (_simpson_sum(n_to_p, 0, p_q, 60) + _simpson_sum(n_to_p, p_q, p_max, 400),
            _simpson_sum(p_to_n, 0, p_q, 60) + _simpson_sum(p_to_n, p_q, p_max, 400))


_DECAY_PHASE_SPACE = _simpson_sum(
    lambda p: p * p * (_Q_ME - math.sqrt(1 + p * p)) ** 2, 0, math.sqrt(_Q_ME ** 2 - 1), 400)  # λ₀ ≈ 1.636

_WEAK_LOG_T_MAX, _WEAK_LOG_T_MIN, _WEAK_POINTS = math.log(40.0), math.log(0.002), 360


@lru_cache(maxsize=1)
def _weak_table() -> tuple[list[float], list[float]]:
    """ln(I n→p) y ln(I p→n) en una rejilla de ln T. Se calcula una vez (~0,5 s) y se reutiliza:
    no dependen de η, de N_ν ni de τ (τ solo multiplica)."""
    log_np, log_pn = [], []
    for i in range(_WEAK_POINTS):
        t = math.exp(_WEAK_LOG_T_MAX + (_WEAK_LOG_T_MIN - _WEAK_LOG_T_MAX) * i / (_WEAK_POINTS - 1))
        a, b = _born_integrals(ELECTRON_MASS_MEV / t,
                               ELECTRON_MASS_MEV / (t * neutrino_temperature_ratio(t)))
        log_np.append(math.log(max(a, 1e-300)))
        log_pn.append(math.log(max(b, 1e-300)))
    return log_np, log_pn


def weak_rates(t_mev: float, neutron_lifetime_s: float = DEFAULT_NEUTRON_LIFETIME_S) -> tuple[float, float]:
    """(λ n→p, λ p→n) en s⁻¹ a la temperatura de los fotones t_mev. Incluyen la desintegración
    del neutrón: a temperatura baja, λ n→p → 1/τ y λ p→n → 0."""
    log_np, log_pn = _weak_table()
    x = (math.log(t_mev) - _WEAK_LOG_T_MAX) / (_WEAK_LOG_T_MIN - _WEAK_LOG_T_MAX) * (_WEAK_POINTS - 1)
    x = min(max(x, 0.0), _WEAK_POINTS - 1.000001)
    i = int(x)
    w = x - i
    norm = 1 / (neutron_lifetime_s * _DECAY_PHASE_SPACE)
    return (norm * math.exp(log_np[i] + w * (log_np[i + 1] - log_np[i])),
            norm * math.exp(log_pn[i] + w * (log_pn[i + 1] - log_pn[i])))


# --- La red nuclear --------------------------------------------------------------------
# Y_i = núcleos de la especie i por barión. La ecuación de cada reacción a + b → c + d es
#   dY_a/dt = −ρ_b·N_A⟨σv⟩·Y_a·Y_b + (inversa)·Y_c·Y_d   (y 1/2 si a = b, para no contar doble)
# con ρ_b la densidad de bariones en g/cm³ (N_A·m_u = 1 g/mol).

def _reaction_coefficients(t_mev: float, eta: float, neutron_lifetime_s: float) -> list[tuple]:
    """(reactivos, productos, k directa, k inversa) de cada reacción a la temperatura t_mev."""
    t9 = kelvin(t_mev) / 1e9
    t9_fit = min(t9, 10.0)       # los ajustes valen hasta T9 = 10; por encima todo está en equilibrio
    rho = baryon_density(t_mev, eta) * ATOMIC_MASS_UNIT_G
    lam_np, lam_pn = weak_rates(t_mev, neutron_lifetime_s)
    out = [((nr.N,), (nr.P,), lam_np, lam_pn)]
    for _name, reac, prod, rate, rev, q9, photon in nr.REACTIONS:
        f = rate(t9_fit)
        same_in = 2 if reac[0] == reac[-1] and len(reac) == 2 else 1
        forward = f * rho ** (len(reac) - 1) / same_in
        if photon:
            reverse = rev * nr.PHOTODISSOCIATION_FACTOR * t9 ** 1.5 * math.exp(-q9 / t9) * f
        elif rev and len(prod) == 2:
            same_out = 2 if prod[0] == prod[1] else 1
            reverse = rev * math.exp(-q9 / t9) * rho * f / same_out
        else:
            reverse = 0.0
        out.append((reac, prod, forward, reverse))
    return out


def _rates_and_jacobian(y: list[float], coefficients: list[tuple]) -> tuple[list[float], list[list[float]]]:
    """dY/dt y su jacobiano ∂(dY_i/dt)/∂Y_j."""
    n = len(y)
    dydt = [0.0] * n
    jac = [[0.0] * n for _ in range(n)]
    for reac, prod, kf, kr in coefficients:
        # Ritmo directo e inverso (reacciones por barión y segundo) y sus derivadas
        if len(reac) == 1:
            flow_f, grad_f = kf * y[reac[0]], ((reac[0], kf),)
        else:
            a, b = reac[0], reac[1]
            flow_f, grad_f = kf * y[a] * y[b], ((a, kf * y[b]), (b, kf * y[a]))
        if kr == 0.0:
            flow_r, grad_r = 0.0, ()
        elif len(prod) == 1:
            flow_r, grad_r = kr * y[prod[0]], ((prod[0], kr),)
        else:
            c, d = prod[0], prod[1]
            flow_r, grad_r = kr * y[c] * y[d], ((c, kr * y[d]), (d, kr * y[c]))
        net = flow_f - flow_r
        for s in reac:
            dydt[s] -= net
            row = jac[s]
            for j, g in grad_f:
                row[j] -= g
            for j, g in grad_r:
                row[j] += g
        for s in prod:
            dydt[s] += net
            row = jac[s]
            for j, g in grad_f:
                row[j] += g
            for j, g in grad_r:
                row[j] -= g
    return dydt, jac


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Resuelve a·x = b (eliminación de Gauss con pivote parcial). Modifica a y b."""
    n = len(b)
    for k in range(n):
        pivot = max(range(k, n), key=lambda r: abs(a[r][k]))
        if pivot != k:
            a[k], a[pivot] = a[pivot], a[k]
            b[k], b[pivot] = b[pivot], b[k]
        akk = a[k][k]
        if akk == 0.0:
            continue
        row_k = a[k]
        for r in range(k + 1, n):
            factor = a[r][k] / akk
            if factor:
                row_r = a[r]
                for c in range(k, n):
                    row_r[c] -= factor * row_k[c]
                b[r] -= factor * b[k]
    x = [0.0] * n
    for k in range(n - 1, -1, -1):
        s = b[k] - sum(a[k][c] * x[c] for c in range(k + 1, n))
        x[k] = s / a[k][k] if a[k][k] else 0.0
    return x


def _newton(y: list[float], base: list[float], gamma_dt: float,
            coefficients: list[tuple]) -> list[float] | None:
    """Resuelve Y − base = γ·dt·F(Y) con el método de Newton. None si no converge."""
    n = len(y)
    guess = list(y)
    for _ in range(15):
        dydt, jac = _rates_and_jacobian(guess, coefficients)
        g = [guess[i] - base[i] - gamma_dt * dydt[i] for i in range(n)]
        matrix = [[(1.0 if i == j else 0.0) - gamma_dt * jac[i][j] for j in range(n)] for i in range(n)]
        delta = _solve(matrix, [-v for v in g])
        converged = True
        for i in range(n):
            new = guess[i] + delta[i]
            if new < 0:
                new = guess[i] * 0.1          # sin abundancias negativas: acercarse al cero
            if abs(new - guess[i]) > 1e-9 * abs(guess[i]) + 1e-30:
                converged = False
            guess[i] = new
        if converged:
            return guess
    return None


def _implicit_step(y: list[float], y_old: list[float] | None, dt: float, dt_old: float | None,
                   coefficients: list[tuple]) -> list[float]:
    """Un paso de BDF2 de paso variable (el primero, Euler implícito), resuelto con Newton.

    BDF2: Y₊ − α·Y + β·Y₋ = γ·dt·F(Y₊). Es estable aunque las reacciones con fotones sean
    10¹⁵ veces más rápidas que el paso, y de segundo orden (el error baja ×4 al dividir el paso).
    Si Newton no converge, el paso se hace en dos mitades con Euler implícito.
    """
    if y_old is None:
        alpha, beta, gamma = 1.0, 0.0, 1.0
    else:
        w = dt / dt_old
        alpha, beta, gamma = (1 + w) ** 2 / (1 + 2 * w), w * w / (1 + 2 * w), (1 + w) / (1 + 2 * w)
    base = [alpha * y[i] - (beta * y_old[i] if y_old else 0.0) for i in range(len(y))]
    result = _newton(y, base, gamma * dt, coefficients)
    if result is not None:
        return result
    half = y
    for _ in range(2):
        half = _newton(half, half, dt / 2, coefficients) or _split_backward_euler(half, dt / 2, coefficients)
    return half


def _split_backward_euler(y: list[float], dt: float, coefficients: list[tuple], depth: int = 0) -> list[float]:
    """Euler implícito partiendo el paso hasta que Newton converja."""
    result = _newton(y, y, dt, coefficients)
    if result is not None or depth > 8:
        return result if result is not None else y
    half = _split_backward_euler(y, dt / 2, coefficients, depth + 1)
    return _split_backward_euler(half, dt / 2, coefficients, depth + 1)


def _temperatures(t_start: float, t_end: float, steps: int) -> list[float]:
    """Temperaturas de cada paso, en progresión geométrica. Hasta 0,5 MeV solo pasan cosas
    lentas (equilibrio n ⇄ p y su congelación): una quinta parte de los pasos basta. El resto
    va a la nucleosíntesis propiamente dicha, por debajo de 0,5 MeV."""
    split = 0.5
    if not t_end < split < t_start:
        return [t_start * (t_end / t_start) ** (i / steps) for i in range(1, steps + 1)]
    hot = max(steps // 5, 1)
    cold = steps - hot
    temps = [t_start * (split / t_start) ** (i / hot) for i in range(1, hot + 1)]
    temps += [split * (t_end / split) ** (i / cold) for i in range(1, cold + 1)]
    return temps


# --- Simulación ----------------------------------------------------------------

def _x(y: list[float], species: int) -> float:
    """Fracción de masa de una especie."""
    return nr.MASS_NUMBER[species] * y[species]


@dataclass(frozen=True)
class Snapshot:
    time_s: float
    temperature_mev: float
    neutron_fraction: float          # X_n: fracción de masa en neutrones libres
    deuterium_fraction: float        # X_D: fracción de masa en deuterio
    helium_fraction: float           # Y:   fracción de masa en helio-4
    equilibrium_fraction: float      # X_n si las reacciones débiles fueran instantáneas
    proton_fraction: float = 0.0     # X_p: protones libres (núcleos de hidrógeno)
    tritium_fraction: float = 0.0    # X_T: tritio (³H), que luego se desintegra en ³He
    helium3_fraction: float = 0.0    # X(³He)
    lithium7_fraction: float = 0.0   # X(⁷Li)
    beryllium7_fraction: float = 0.0  # X(⁷Be), que luego captura un electrón y da ⁷Li

    @property
    def temperature_k(self) -> float:
        return kelvin(self.temperature_mev)

    @property
    def neutron_to_proton(self) -> float:
        """n/p contando solo nucleones libres."""
        return self.neutron_fraction / self.proton_fraction

    @property
    def deuterium_to_hydrogen(self) -> float:
        """D/H en número de núcleos (lo que miden los astrónomos)."""
        return (self.deuterium_fraction / 2) / self.proton_fraction

    @property
    def helium3_to_hydrogen(self) -> float:
        """³He/H, contando el tritio, que acaba siendo ³He (semivida de 12 años)."""
        return (self.helium3_fraction + self.tritium_fraction) / 3 / self.proton_fraction

    @property
    def lithium7_to_hydrogen(self) -> float:
        """⁷Li/H, contando el ⁷Be, que acaba siendo ⁷Li (semivida de 53 días)."""
        return (self.lithium7_fraction + self.beryllium7_fraction) / 7 / self.proton_fraction

    @property
    def unburned_neutrons(self) -> float:
        """Neutrones (por barión) que todavía no están dentro de un helio-4."""
        return (self.neutron_fraction + self.deuterium_fraction / 2 + 2 * self.tritium_fraction / 3
                + self.helium3_fraction / 3 + 4 * self.lithium7_fraction / 7 + 3 * self.beryllium7_fraction / 7)


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
        """Y_p: fracción de masa de helio-4 primordial, con las correcciones a las tasas débiles."""
        return self.final.helium_fraction * WEAK_CORRECTION_HELIUM

    @property
    def helium_fraction_born(self) -> float:
        """Y_p tal como sale de la red, con las tasas débiles de Born (sin corregir)."""
        return self.final.helium_fraction

    @property
    def hydrogen_fraction(self) -> float:
        return self.final.proton_fraction - (self.helium_fraction - self.helium_fraction_born)

    @property
    def deuterium_to_hydrogen(self) -> float:
        return self.final.deuterium_to_hydrogen

    @property
    def helium3_to_hydrogen(self) -> float:
        return self.final.helium3_to_hydrogen

    @property
    def lithium7_to_hydrogen(self) -> float:
        return self.final.lithium7_to_hydrogen

    def event(self, name: str) -> Event:
        return next(e for e in self.events if e.name == name)

    def at_temperature(self, t_mev: float) -> Snapshot:
        """Instantánea más cercana a una temperatura dada."""
        return min(self.history, key=lambda s: abs(math.log(s.temperature_mev / t_mev)))


def simulate(eta: float = DEFAULT_ETA,
             neutron_lifetime_s: float = DEFAULT_NEUTRON_LIFETIME_S,
             neutrino_species: float = DEFAULT_NEUTRINO_SPECIES,
             t_start_mev: float = 20.0, t_end_mev: float = 0.01,
             steps: int = 2500) -> NucleosynthesisResult:
    """Simula la nucleosíntesis desde T = 20 MeV (t ≈ 2 ms) hasta T = 0.01 MeV (~3.5 h)."""
    if not 1e-12 < eta < 1e-7:
        raise ValueError("eta must be between 1e-12 and 1e-7 (measured: 6.1e-10).")
    if neutron_lifetime_s <= 0:
        raise ValueError("The neutron lifetime must be positive.")
    if not 0 <= neutrino_species <= 10:
        raise ValueError("The number of neutrino species must be between 0 and 10.")

    result = NucleosynthesisResult(eta, neutron_lifetime_s, neutrino_species)

    temp = t_start_mev
    t = 1 / (2 * hubble_rate(temp, neutrino_species))   # universo de radiación: t = 1/(2H)
    xn = equilibrium_neutron_fraction(temp)
    y = [0.0] * len(nr.SPECIES)
    y[nr.N], y[nr.P] = xn, 1 - xn
    y_old, dt_old = None, None

    def snap() -> Snapshot:
        return Snapshot(t, temp, _x(y, nr.N), _x(y, nr.D), _x(y, nr.HE4),
                        equilibrium_neutron_fraction(temp), _x(y, nr.P), _x(y, nr.T),
                        _x(y, nr.HE3), _x(y, nr.LI7), _x(y, nr.BE7))

    result.history.append(snap())
    frozen = False
    for new_temp in _temperatures(t_start_mev, t_end_mev, steps):
        # Tiempo transcurrido: d ln a = −d ln T_ν (los neutrinos se enfrían como 1/a)
        tnu_old = temp * neutrino_temperature_ratio(temp)
        tnu_new = new_temp * neutrino_temperature_ratio(new_temp)
        h_mid = hubble_rate(math.sqrt(temp * new_temp), neutrino_species)
        dt = math.log(tnu_old / tnu_new) / h_mid
        temp, t = new_temp, t + dt

        coefficients = _reaction_coefficients(temp, eta, neutron_lifetime_s)
        y, y_old, dt_old = _implicit_step(y, y_old, dt, dt_old, coefficients), y, dt

        if not frozen:
            lam_np, lam_pn = coefficients[0][2], coefficients[0][3]
            if lam_np + lam_pn < h_mid:
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
        lam_np, lam_pn = weak_rates(cur.temperature_mev, neutron_lifetime_s)
        p_np = 1 - math.exp(-lam_np * dt)
        p_pn = 1 - math.exp(-lam_pn * dt)
        n_to_p = _binomial(neutrons, p_np, rng)
        p_to_n = _binomial(protons, p_pn, rng)
        neutrons += p_to_n - n_to_p
        protons += n_to_p - p_to_n

        # Probabilidad de que un neutrón sin quemar acabe en helio en este paso,
        # tomada de la simulación exacta (lo que se "quemó" en ese mismo paso).
        unburned_prev = prev.unburned_neutrons
        unburned_cur = cur.unburned_neutrons
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


