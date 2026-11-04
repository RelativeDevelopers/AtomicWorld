"""
El núcleo atómico: dónde poner los nucleones y cómo dibujar cada uno.

Física:
  - Radio nuclear R = 1,2 fm · A^(1/3) (atomicworld.atoms).
  - Cada nucleón es una nube difusa: perfil exponencial de radio cuadrático medio
    0,84 fm (radio de carga del protón).
  - Los nucleones están a ~1,75 fm entre centros: la densidad nuclear (~0,16
    nucleones/fm³, ~2×10¹⁷ kg/m³) es casi la misma en todos los núcleos, como en una gota.
  - Modo realista: densidad del núcleo entero con el perfil de Woods–Saxon, que es lo
    que miden los experimentos de dispersión de electrones.

Limitación: empaquetado aleatorio (modelo de "gota líquida"); los núcleos reales tienen
estructura de capas y, en el C-12, agrupaciones alfa.
"""
import numpy as np

NUCLEON_RMS_FM = 0.84
NUCLEON_A_FM = NUCLEON_RMS_FM / np.sqrt(12)     # ρ ∝ e^(-r/a) tiene r_rms = a·√12
NUCLEON_SPACING_FM = 1.75
WS_DIFFUSENESS_FM = 0.55                        # grosor de la "piel" del núcleo


def directions(count, rng):
    v = rng.normal(size=(count, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def sample_exponential(count, a, rng):
    """Radios con densidad ρ(r) ∝ e^(-r/a): r² e^(-r/a) es una Gamma(3, a)."""
    return rng.gamma(3.0, a, count)


def sample_woods_saxon(count, radius, a, rng):
    r = np.linspace(0, radius + 10 * a, 4000)
    p = r * r / (1 + np.exp((r - radius) / a))
    cdf = np.cumsum(p)
    cdf /= cdf[-1]
    return np.interp(rng.random(count), cdf, r)


def pack_nucleons(a_count: int, radius: float, rng) -> np.ndarray:
    """Coloca A esferas a ~NUCLEON_SPACING_FM dentro de una esfera de radio R (fm)."""
    if a_count == 1:
        return np.zeros((1, 3))
    inner = max(radius - 0.7, 0.4)
    pos = directions(a_count, rng) * (rng.random((a_count, 1)) ** (1 / 3)) * inner
    not_self = 1 - np.eye(a_count)
    iterations = 400 if a_count <= 100 else 250
    for _ in range(iterations):
        diff = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(diff, axis=2) + np.eye(a_count)
        overlap = np.clip(NUCLEON_SPACING_FM - dist, 0, None) * not_self
        pos += (diff / dist[..., None] * overlap[..., None]).sum(axis=1) * 0.5
        pos -= pos.mean(axis=0) * 0.1                    # mantener centrado
        r = np.linalg.norm(pos, axis=1, keepdims=True)
        pos = np.where(r > inner, pos / np.maximum(r, 1e-9) * inner, pos)
    return pos


def assign_kinds(protons: int, neutrons: int, rng) -> np.ndarray:
    """'p' o 'n' para cada posición, mezclados al azar."""
    kinds = np.array(["p"] * protons + ["n"] * neutrons)
    return kinds[rng.permutation(len(kinds))]


def points_per_nucleon(a_count: int, budget: int = 400_000) -> int:
    return int(np.clip(budget // a_count, 1500, 6000))


def nucleon_clouds(centers, ppn: int, rng):
    """Puntos de cada nucleón alrededor de su centro. Devuelve (posiciones, índice del nucleón)."""
    pos = [c + directions(ppn, rng) * sample_exponential(ppn, NUCLEON_A_FM, rng)[:, None]
           for c in centers]
    owner = np.repeat(np.arange(len(centers)), ppn)
    return np.vstack(pos), owner


def strong_bonds(centers, max_range_fm: float = 2.0):
    """Pares de nucleones vecinos (a menos del alcance de la fuerza fuerte)."""
    i, j = np.triu_indices(len(centers), 1)
    d = np.linalg.norm(centers[i] - centers[j], axis=1)
    keep = d < max_range_fm
    return centers[i[keep]], centers[j[keep]]


def density_kg_m3(a_count: int, radius_fm: float) -> float:
    return a_count * 1.66053906892e-27 / (4 / 3 * np.pi * (radius_fm * 1e-15) ** 3)
