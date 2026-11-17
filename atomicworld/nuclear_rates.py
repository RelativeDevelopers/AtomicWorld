"""Tasas de las reacciones nucleares de la nucleosíntesis primordial.

Cada función recibe T9 (temperatura en 10⁹ K) y devuelve N_A⟨σv⟩ en cm³·mol⁻¹·s⁻¹ (para dos
partículas que chocan) o en s⁻¹ (desintegraciones). Son ajustes y tablas PUBLICADOS: la fuente
de cada uno va en su comentario y en docs/TECNICO.md. Las fórmulas se han pasado a Python desde
AlterBBN 2.2 (Arbey et al., arXiv:1806.11095), que reúne las mismas fuentes, y se comparan con
AlterBBN en los tests.

La reacción inversa de cada una (por ejemplo, el fotón que rompe el deuterio: D + γ → n + p) no
se mide: se deduce por balance detallado con los coeficientes REV y Q9 de la tabla REACTIONS.

Como el resto del núcleo, este módulo no imprime nada.
"""
import math
from bisect import bisect_right

# --- Núcleos de la red ---------------------------------------------------------------
# Y_i = (número de núcleos i) / (número de bariones). Fracción de masa X_i = A_i · Y_i.
N, P, D, T, HE3, HE4, LI7, BE7 = range(8)
SPECIES = ("n", "p", "D", "T", "He3", "He4", "Li7", "Be7")
MASS_NUMBER = (1, 1, 2, 3, 3, 4, 7, 7)


def _clip(x: float) -> float:
    return x if x > 0 else 0.0


def _table(grid: tuple, values: tuple):
    """Interpolación log-log en una tabla (T9, N_A⟨σv⟩). Fuera de la tabla, el valor del borde."""
    log_grid = [math.log(x) for x in grid]
    log_values = [math.log(v) for v in values]

    def rate(t9: float) -> float:
        if t9 <= grid[0]:
            return values[0]
        if t9 >= grid[-1]:
            return values[-1]
        x = math.log(t9)
        i = bisect_right(log_grid, x) - 1
        w = (x - log_grid[i]) / (log_grid[i + 1] - log_grid[i])
        return math.exp(log_values[i] + w * (log_values[i + 1] - log_values[i]))
    return rate


# Rejilla de T9 de las tablas de Coc et al. (2015)
_COC_GRID = (
    0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.011, 0.012, 0.013,
    0.014, 0.015, 0.016, 0.018, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11,
    0.12, 0.13, 0.14, 0.15, 0.16, 0.18, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9,
    1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)

# D(p,γ)³He: Coc et al. (2015)
_rate_d_p = _table(_COC_GRID, (
    4.815e-14, 6.409e-09, 4.525e-07, 4.896e-06, 2.444e-05, 8.086e-05, 0.0002078, 0.0004499,
    0.0008619, 0.001506, 0.00245, 0.003767, 0.005531, 0.007816, 0.0107, 0.01425, 0.02366,
    0.03659, 0.08753, 0.1701, 0.4476, 0.8915, 1.51, 2.302, 3.265, 4.392, 5.676, 7.109, 8.685,
    10.4, 12.24, 14.2, 16.28, 20.76, 25.65, 39.41, 55.05, 72.25, 90.76, 110.4, 131, 174.8,
    221.2, 270, 320.7, 372.9, 509.3, 652.2, 800, 951.7, 1265, 1587, 1914, 2244, 2905, 3557,
    4194, 4812, 5410, 5988))

# D(d,n)³He: Coc et al. (2015)
_rate_dd_n = _table(_COC_GRID, (
    1.142e-08, 5.47e-05, 0.003021, 0.03732, 0.2212, 0.8546, 2.505, 6.066, 12.78, 24.24, 42.37,
    69.36, 107.7, 160, 229.1, 317.9, 566.7, 931, 2504, 5301, 1.568e+04, 3.369e+04, 6.013e+04,
    9.527e+04, 1.39e+05, 1.912e+05, 2.513e+05, 3.19e+05, 3.938e+05, 4.753e+05, 5.631e+05,
    6.568e+05, 7.559e+05, 9.691e+05, 1.2e+06, 1.842e+06, 2.555e+06, 3.318e+06, 4.119e+06,
    4.946e+06, 5.792e+06, 7.517e+06, 9.26e+06, 1.1e+07, 1.272e+07, 1.442e+07, 1.85e+07,
    2.235e+07, 2.595e+07, 2.932e+07, 3.546e+07, 4.093e+07, 4.585e+07, 5.031e+07, 5.816e+07,
    6.488e+07, 7.072e+07, 7.583e+07, 8.037e+07, 8.437e+07))

# D(d,p)T: Coc et al. (2015). En T9 = 1,5 la copia de AlterBBN dice 2.882e7, una errata
# evidente (la tabla crece y sus vecinos son 1.565e7 y 2.181e7): aquí va 1.882e7.
_rate_dd_p = _table(_COC_GRID, (
    1.173e-08, 5.609e-05, 0.003092, 0.03814, 0.2257, 0.8707, 2.549, 6.164, 12.97, 24.58, 42.9,
    70.16, 108.8, 161.5, 231, 320.2, 569.8, 934.3, 2502, 5276, 1.549e+04, 3.307e+04, 5.868e+04,
    9.246e+04, 1.343e+05, 1.837e+05, 2.404e+05, 3.039e+05, 3.737e+05, 4.493e+05, 5.304e+05,
    6.165e+05, 7.072e+05, 9.011e+05, 1.11e+06, 1.682e+06, 2.309e+06, 2.974e+06, 3.663e+06,
    4.371e+06, 5.089e+06, 6.543e+06, 8.001e+06, 9.448e+06, 1.087e+07, 1.228e+07, 1.565e+07,
    1.882e+07, 2.181e+07, 2.461e+07, 2.976e+07, 3.44e+07, 3.863e+07, 4.251e+07, 4.946e+07,
    5.552e+07, 6.077e+07, 6.529e+07, 6.912e+07, 7.228e+07))


# --- Reacciones con neutrones -------------------------------------------------------------

def rate_n_p(t9: float) -> float:
    """p(n,γ)D. Ando et al., Phys. Rev. C 74, 025809 (2006); por encima de T9 = 1,5,
    Smith, Kawano y Malaney, ApJS 85, 219 (1993)."""
    if t9 <= 1.5:
        return 44216.0 * (1 + 3.75191 * t9 + 1.92934 * t9 ** 2 + 0.746503 * t9 ** 3
                          + 0.0197023 * t9 ** 4 + 3.00491e-6 * t9 ** 5) / (
            1 + 5.4678 * t9 + 5.62395 * t9 ** 2 + 0.489312 * t9 ** 3 + 0.00747806 * t9 ** 4)
    s = math.sqrt(t9)
    return 47420.0 * (1 - 0.8504 * s + 0.4895 * t9 - 0.09623 * t9 * s + 0.008471 * t9 ** 2
                      - 2.8e-4 * t9 ** 2 * s)


def rate_d_n(t9: float) -> float:
    """D(n,γ)T. Wagoner, ApJS 18, 247 (1969)."""
    return 66.2 * (1 + 18.9 * t9)


def rate_he3_n_gamma(t9: float) -> float:
    """³He(n,γ)⁴He. Wagoner (1969)."""
    return 6.62 * (1 + 905.0 * t9)


def rate_he3_n_p(t9: float) -> float:
    """³He(n,p)T. Serpico et al., JCAP 12, 010 (2004)."""
    if t9 >= 2.5:
        return 4.81732e8
    s = math.sqrt(t9)
    return _clip(7.064935e8 + 6.733213571736319e8 * t9 + 1.7181155480346258e9 * t9 ** 2
                 - 4.5367658146835446e8 * t9 ** 3 - 1.2216728981712557e8 * t9 ** 4
                 - 4.92736677238425e8 * s - 1.3659670893994067e9 * t9 * s
                 - 6.629932739639357e8 * t9 ** 2 * s + 4.834951929033479e8 * t9 ** 3 * s)


def rate_be7_n_p(t9: float) -> float:
    """⁷Be(n,p)⁷Li. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 1.28039e9
    s = math.sqrt(t9)
    return _clip(6.8423032e9 + 1.7674863e10 * t9 + 2.6622006e9 * t9 ** 2 - 3.3561608e8 * t9 ** 3
                 - 5.9309139e6 * t9 ** 4 - 1.4987996e10 * s - 1.0576906e10 * t9 * s
                 + 2.7447598e8 * t9 ** 2 * s + 7.6425157e7 * t9 ** 3 * s
                 - 2.282944e7 * t9 ** -1.5 / math.exp(0.050351813 / t9))


def rate_be7_n_alpha(t9: float) -> float:
    """⁷Be(n,α)⁴He. Hou et al., Phys. Rev. C 91, 055802 (2015)."""
    if t9 > 10:
        return 0.0
    c = t9 ** (1 / 3)
    return math.exp(-17.8984 + 0.2711 / t9 - 23.8918 / c + 62.2135 * c - 5.2888 * t9
                    + 0.3869 * t9 * c * c - 22.6197 * math.log(t9))


# --- Reacciones con protones ---------------------------------------------------------------

def rate_d_p(t9: float) -> float:
    """D(p,γ)³He. Tabla de Coc et al., Phys. Rev. D 92, 123526 (2015)."""
    return _rate_d_p(t9)


def rate_t_p(t9: float) -> float:
    """T(p,γ)⁴He. Caughlan y Fowler, At. Data Nucl. Data Tables 40, 283 (1988)."""
    c = t9 ** (1 / 3)
    return 2.2e4 / (c * c) * math.exp(-3.869 / c) * (
        1 + 0.108 * c + 1.68 * c * c + 1.26 * t9 + 0.551 * t9 * c + 1.06 * t9 * c * c)


def rate_li7_p_alpha(t9: float) -> float:
    """⁷Li(p,α)⁴He. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 1.53403e6 + 84516.7
    c = t9 ** (1 / 3)
    first = (-8.9654123e7 - 2.5851582e8 * t9 - 2.6831252e7 * t9 ** 2 + 3.8691673e8 * c
             + 4.9721269e8 * c ** 2 + 2.6444808e7 * c ** 4 - 1.2946419e6 * c ** 5
             - 1.0941088e8 * c ** 7 + 9.9899564e7 * c ** 8) / (c * c) / math.exp(7.73389632 / c)
    poly = (3.0014189e7 - 1.8366119e8 * t9 + 1.7688138e9 * t9 ** 2 - 8.4772261e9 * t9 ** 3
            + 2.0237351e10 * t9 ** 4 - 1.9650068e10 * t9 ** 5 + 7.9452762e8 * t9 ** 6
            + 1.3132468e10 * t9 ** 7 - 8.209351e9 * t9 ** 8 - 9.1099236e8 * t9 ** 9
            + 2.7814079e9 * t9 ** 10 - 1.0785293e9 * t9 ** 11 + 1.3993392e8 * t9 ** 12)
    second = math.exp(-1.137519 * t9 ** 2 - 8.6256687 / c) * poly / (c * c)
    return _clip(first + second)


# --- Reacciones con partículas alfa -------------------------------------------------------

def rate_t_alpha(t9: float) -> float:
    """T(α,γ)⁷Li. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 807.406
    poly = (0.094614248 - 4.9273133 * t9 + 99.358965 * t9 ** 2 - 989.81236 * t9 ** 3
            + 4368.45 * t9 ** 4 + 931.93597 * t9 ** 5 - 391.07855 * t9 ** 6 + 159.23101 * t9 ** 7
            - 34.407594 * t9 ** 8 + 3.3919004 * t9 ** 9 + 0.017556217 * t9 ** 10
            - 0.036253427 * t9 ** 11 + 0.0031118827 * t9 ** 12 - 0.00008714468 * t9 ** 13)
    return _clip(poly / math.sqrt(t9) / (math.exp(8.4e-7 * t9) * (1 + 1.78616593 * t9) ** 3))


def rate_he3_alpha(t9: float) -> float:
    """³He(α,γ)⁷Be. Cyburt y Davids, Phys. Rev. C 78, 064614 (2008)."""
    if t9 > 100:
        return 0.0
    c2 = t9 ** (2 / 3)
    return math.exp(15.609867 - 12.82707707 / t9 ** (1 / 3) - 0.6666667 * math.log(t9)) * (
        (1 - 0.020478 * c2 + 0.211995 * c2 * c2) / (1 + 0.255059 * c2 + 0.338573 * c2 * c2))


# --- Reacciones con deuterio ----------------------------------------------------------------

def rate_dd_n(t9: float) -> float:
    """D(d,n)³He. Tabla de Coc et al. (2015)."""
    return _rate_dd_n(t9)


def rate_dd_p(t9: float) -> float:
    """D(d,p)T. Tabla de Coc et al. (2015)."""
    return _rate_dd_p(t9)


def rate_t_d(t9: float) -> float:
    """T(d,n)⁴He. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 3.40249e8
    c = t9 ** (1 / 3)
    return _clip(6.2265733e8 / (math.exp(0.49711597 / t9) * t9 ** 0.56785403)
                 + math.exp(-0.23309803 * t9 ** 2 - 1.342742 / c) * (
                     -8.1144927e7 + 2.2315324e9 * t9 - 2.9439669e9 * t9 ** 2 + 1.8764462e9 * t9 ** 3
                     - 6.0511612e8 * t9 ** 4 + 9.5196576e7 * t9 ** 5 - 5.2901086e6 * t9 ** 6) / (c * c))


def rate_he3_d(t9: float) -> float:
    """³He(d,p)⁴He. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 1.55167e8
    c = t9 ** (1 / 3)
    poly = (-3.1335916e7 - 6.2051071e8 * t9 - 1.8782248e9 * t9 ** 2 + 6.5642773e8 * t9 ** 3
            + 1.530887e8 * t9 ** 4 - 4.9542138e8 * c ** 10 - 1.770285e8 * c ** 11
            + 1.14185e8 * c - 2.516526e7 * c ** 13 + 1.7500204e8 * c ** 2
            - 1.7513362e9 * c ** 4 + 5.2792247e9 * c ** 5 - 3.32382e9 * c ** 7
            + 2.0346284e9 * c ** 8)
    return _clip(3.1038385e8 / (math.exp(1.6190981 / t9) * t9 ** 0.12159455)
                 + math.exp(-0.0062340825 * t9 ** 2 - 1.4540617 / c) * poly / (c * c))


def rate_he3_he3(t9: float) -> float:
    """³He(³He,2p)⁴He. NACRE, Angulo et al., Nucl. Phys. A 656, 3 (1999)."""
    c = t9 ** (1 / 3)
    return _clip(5.59e10 / (c * c) * math.exp(-12.277 / c)
                 * (1 - 0.135 * t9 + 2.54e-2 * t9 ** 2 - 1.29e-3 * t9 ** 3))


def rate_li7_d(t9: float) -> float:
    """⁷Li(d,nα)⁴He. Serpico et al. (2004)."""
    if t9 >= 2.5:
        return 1.37518e9
    c = t9 ** (1 / 3)
    return _clip(1.66e11 / (c * c) * math.exp(-10.254 / c) + 1.71e6 * t9 ** -1.5 * math.exp(-3.246 / t9)
                 + 1.49e10 * t9 ** -1.5 * math.exp(-4.0894 / t9)
                 * (2.57e-2 / t9 + 2.6314 / (c * c) - 4.1929 / c - 2.1241 + 4.1136 * c))


def rate_be7_d(t9: float) -> float:
    """⁷Be(d,pα)⁴He. Caughlan y Fowler (1988)."""
    c = t9 ** (1 / 3)
    return 1.07e12 / (c * c) * math.exp(-12.428 / c)


# --- La red ------------------------------------------------------------------------------
# (nombre, reactivos, productos, tasa, REV, Q9, ¿la inversa es una fotodesintegración?)
#
# Balance detallado (Wagoner 1969; Kawano 1992): si la reacción directa tiene N_A⟨σv⟩ = f,
#   inversa con fotón (c + γ → a + b):   λ = REV · 0,987·10¹⁰ · T9^(3/2) · e^(−Q9/T9) · f   [s⁻¹]
#   inversa de dos cuerpos (c + d → a + b):  N_A⟨σv⟩ = REV · e^(−Q9/T9) · f
# REV sale de los espines y las masas; Q9 es la energía liberada en unidades de 10⁹ K.
# Las reacciones con tres productos no tienen inversa (Q9 > 170: no ocurre).
REACTIONS = (
    ("p(n,γ)D",       (N, P),     (D,),          rate_n_p,          0.477, 25.815,  True),
    ("D(n,γ)T",       (D, N),     (T,),          rate_d_n,          1.65,  72.612,  True),
    ("³He(n,γ)⁴He",   (HE3, N),   (HE4,),        rate_he3_n_gamma,  2.63,  238.794, True),
    ("³He(n,p)T",     (HE3, N),   (P, T),        rate_he3_n_p,      1.001, 8.863,   False),
    ("⁷Be(n,p)⁷Li",   (BE7, N),   (P, LI7),      rate_be7_n_p,      1.001, 19.080,  False),
    ("⁷Be(n,α)⁴He",   (BE7, N),   (HE4, HE4),    rate_be7_n_alpha,  4.68,  220.382, False),
    ("D(p,γ)³He",     (D, P),     (HE3,),        rate_d_p,          1.65,  63.749,  True),
    ("T(p,γ)⁴He",     (T, P),     (HE4,),        rate_t_p,          2.63,  229.931, True),
    ("⁷Li(p,α)⁴He",   (LI7, P),   (HE4, HE4),    rate_li7_p_alpha,  4.68,  201.302, False),
    ("T(α,γ)⁷Li",     (T, HE4),   (LI7,),        rate_t_alpha,      1.13,  28.629,  True),
    ("³He(α,γ)⁷Be",   (HE3, HE4), (BE7,),        rate_he3_alpha,    1.13,  18.412,  True),
    ("D(d,n)³He",     (D, D),     (N, HE3),      rate_dd_n,         1.73,  37.934,  False),
    ("D(d,p)T",       (D, D),     (P, T),        rate_dd_p,         1.73,  46.798,  False),
    ("T(d,n)⁴He",     (T, D),     (N, HE4),      rate_t_d,          5.51,  204.116, False),
    ("³He(d,p)⁴He",   (HE3, D),   (P, HE4),      rate_he3_d,        5.51,  212.979, False),
    ("³He(³He,2p)⁴He", (HE3, HE3), (P, P, HE4),  rate_he3_he3,      0.0,   0.0,     False),
    ("⁷Li(d,nα)⁴He",  (LI7, D),   (N, HE4, HE4), rate_li7_d,        0.0,   0.0,     False),
    ("⁷Be(d,pα)⁴He",  (BE7, D),   (P, HE4, HE4), rate_be7_d,        0.0,   0.0,     False),
)

PHOTODISSOCIATION_FACTOR = 0.987e10   # (m_u k T / 2πħ²)^{3/2} / N_A con T en 10⁹ K, en mol/cm³
