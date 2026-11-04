"""
Nubes de electrones: puntos muestreados de la densidad de probabilidad |ψ|².

Modelo (aproximación de "átomo aislado"):
  - Cada electrón ocupa un orbital hidrogenoide (n, l) con la carga nuclear efectiva
    Z_ef de las reglas de Slater (atomicworld.atoms).
  - Radial: R_nl(r) del átomo de hidrógeno, para cualquier n ≤ 7 (polinomios de Laguerre
    generalizados), con sus nodos. Slater ajustó sus Z_ef para orbitales de otra forma
    (r^(n*−1)·e^(−Z_ef·r/n*), con un n efectivo n* = 3,7 / 4,0 / 4,2 para n = 4 / 5 / 6) y
    con la R_nl hidrogenoide tal cual las capas n ≥ 3 salen demasiado grandes (el 7s del
    uranio, ~1 nm). Por eso se usa una Z escalada para que cada orbital tenga el radio medio
    del orbital de Slater: <r> = n*(2n*+1)/(2 Z_ef) radios de Bohr.
  - Angular:
      * modo realista: promedio esférico (un átomo aislado en su estado fundamental,
        promediado sobre orientaciones, tiene densidad esférica).
      * modo didáctico: los orbitales reales p (3), d (5) y f (7), con la forma de sus
        armónicos esféricos reales |Y_lm|², ocupados según la regla de Hund. Un subnivel
        lleno suma una densidad esférica (teorema de Unsöld): sale solo, sin forzarlo.

Limitaciones: en los átomos pesados faltan los efectos relativistas (los electrones
internos del oro o del uranio van a una fracción apreciable de la velocidad de la luz),
y Slater es una aproximación de 1930. La forma general y los tamaños son correctos.
"""
import numpy as np

from atomicworld.atoms import slater_zeff

BOHR_PM = 52.9177210544          # radio de Bohr en picómetros (CODATA 2022)
GRID = 6000
# n efectivo de Slater (1930). Para n = 7 Slater no dio valor: 4,3 es la extensión habitual.
N_STAR = {1: 1.0, 2: 2.0, 3: 3.0, 4: 3.7, 5: 4.0, 6: 4.2, 7: 4.3}


def orbital_z(n: int, l: int, zeff: float) -> float:
    """Z de la función hidrogenoide que da al orbital (n, l) el radio medio de Slater."""
    ns = N_STAR[n]
    return zeff * (3 * n * n - l * (l + 1)) / (ns * (2 * ns + 1))


def _laguerre(k: int, alpha: float, x: np.ndarray) -> np.ndarray:
    """Polinomio de Laguerre generalizado L_k^alpha(x), por recurrencia."""
    if k == 0:
        return np.ones_like(x)
    prev, cur = np.ones_like(x), 1 + alpha - x
    for i in range(1, k):
        prev, cur = cur, ((2 * i + 1 + alpha - x) * cur - (i + alpha) * prev) / (i + 1)
    return cur


def radial(n: int, l: int, z: float, r: np.ndarray) -> np.ndarray:
    """R_nl(r) hidrogenoide sin normalizar; r en radios de Bohr."""
    rho = 2 * z * r / n
    return rho ** l * np.exp(-rho / 2) * _laguerre(n - l - 1, 2 * l + 1, rho)


def sample_radius(n: int, l: int, z: float, count: int, rng) -> np.ndarray:
    """Radios (pm) muestreados de P(r) = r² |R_nl|² por transformada inversa."""
    r_max = (9.0 * n * n + 6.0) / z
    r = np.linspace(0, r_max, GRID)
    p = r * r * radial(n, l, z, r) ** 2
    cdf = np.cumsum(p)
    cdf /= cdf[-1]
    return np.interp(rng.random(count), cdf, r) * BOHR_PM


def directions(count: int, rng) -> np.ndarray:
    v = rng.normal(size=(count, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# --- Orbitales reales: parte angular ---------------------------------------------
# Armónicos esféricos reales escritos con la dirección (x, y, z) de módulo 1. Solo importa
# la forma: cada orbital se muestrea por separado y luego se reparte el mismo número de
# puntos por electrón, así que la normalización de cada uno no hace falta.

ORBITALS = {
    0: [("s", lambda x, y, z: np.ones_like(x))],
    1: [("px", lambda x, y, z: x),
        ("py", lambda x, y, z: y),
        ("pz", lambda x, y, z: z)],
    2: [("dz²", lambda x, y, z: 3 * z * z - 1),
        ("dxz", lambda x, y, z: x * z),
        ("dyz", lambda x, y, z: y * z),
        ("dxy", lambda x, y, z: x * y),
        ("dx²−y²", lambda x, y, z: x * x - y * y)],
    3: [("fz³", lambda x, y, z: z * (5 * z * z - 3)),
        ("fxz²", lambda x, y, z: x * (5 * z * z - 1)),
        ("fyz²", lambda x, y, z: y * (5 * z * z - 1)),
        ("fxyz", lambda x, y, z: x * y * z),
        ("fz(x²−y²)", lambda x, y, z: z * (x * x - y * y)),
        ("fx(x²−3y²)", lambda x, y, z: x * (x * x - 3 * y * y)),
        ("fy(3x²−y²)", lambda x, y, z: y * (3 * x * x - y * y))],
}
_MAX_CACHE: dict = {}


def orbital_names(l: int) -> list[str]:
    return [name for name, _ in ORBITALS[l]]


def _angular_max(l: int, k: int) -> float:
    """Máximo de |Y|² sobre la esfera (numérico, con margen), para el muestreo por rechazo."""
    if (l, k) not in _MAX_CACHE:
        d = directions(200_000, np.random.default_rng(12345))
        f = ORBITALS[l][k][1](d[:, 0], d[:, 1], d[:, 2])
        _MAX_CACHE[(l, k)] = float((f * f).max()) * 1.02
    return _MAX_CACHE[(l, k)]


def orbital_directions(l: int, k: int, count: int, rng) -> np.ndarray:
    """Direcciones con densidad angular |Y_lk|² (método de rechazo)."""
    if l == 0:
        return directions(count, rng)
    fn, top = ORBITALS[l][k][1], _angular_max(l, k)
    out, have = [], 0
    while have < count:
        d = directions(max(count * 4, 1000), rng)
        f = fn(d[:, 0], d[:, 1], d[:, 2])
        keep = d[rng.random(len(d)) * top < f * f]
        out.append(keep)
        have += len(keep)
    return np.vstack(out)[:count]


def hund_occupancy(l: int, electrons: int) -> list[int]:
    """Regla de Hund: primero un electrón en cada orbital (↑) y luego se emparejan (↑↓).

    Con el subnivel a medio llenar hay varios estados igual de buenos (en un átomo aislado
    ninguna orientación es especial): este es uno de ellos, siempre el mismo.
    """
    orbitals = 2 * l + 1
    occ = [0] * orbitals
    for i in range(electrons):
        occ[i % orbitals] += 1
    return occ


def p_occupancy(electrons: int) -> list[int]:
    return hund_occupancy(1, electrons)


def points_per_electron(electrons: int, budget: int = 120_000) -> int:
    """Reparte un presupuesto fijo de puntos: el hidrógeno no queda vacío y el oganesón
    (118 electrones) no satura la gráfica."""
    return int(np.clip(budget // electrons, 1000, 30_000))


def mean_radius_pm(n: int, l: int, zeff: float) -> float:
    """Radio medio del orbital (el de Slater): <r> = a₀ · n*(2n*+1) / (2 Z_ef)."""
    ns = N_STAR[n]
    return BOHR_PM * ns * (2 * ns + 1) / (2 * zeff)


def didactic_points(z: int, shells, budget: int = 220_000) -> dict:
    """Puntos por electrón de cada subnivel en el modo didáctico.

    Con el mismo número de puntos por electrón, en un átomo pesado los electrones internos
    (muchos y apretados) brillan muchísimo y las capas externas (pocos electrones repartidos
    en un volumen enorme) casi no se ven. Aquí cada subnivel recibe más puntos cuanto mayor
    es: así se ven todas las capas. El modo realista NO hace esto: allí el brillo es la
    densidad de verdad.
    """
    radii = {(s.n, s.l): mean_radius_pm(s.n, s.l, slater_zeff(z, shells, s.n, s.l)) for s in shells}
    biggest = max(radii.values())
    weight = {k: max((r / biggest) ** 1.5, 0.03) for k, r in radii.items()}
    total = sum(s.electrons * weight[(s.n, s.l)] for s in shells)
    return {k: int(np.clip(budget * w / total, 150, 60_000)) for k, w in weight.items()}


def sample_atom(z: int, shells, ppe, didactic: bool, rng=None):
    """Puntos de todos los electrones del átomo.

    ppe: puntos por electrón, un número o un diccionario {(n, l): puntos}.
    Devuelve (posiciones_pm (N,3), capa n (N,), forma l (N,)).
    """
    rng = rng or np.random.default_rng()
    pos, ns, ls = [], [], []
    per_electron = ppe if isinstance(ppe, dict) else {(s.n, s.l): ppe for s in shells}
    for sh in shells:
        ppe = per_electron[(sh.n, sh.l)]
        zeff = orbital_z(sh.n, sh.l, slater_zeff(z, shells, sh.n, sh.l))
        if didactic and sh.l >= 1:
            # cada orbital real con sus electrones (los puntos de un subnivel quedan seguidos)
            for k, occ in enumerate(hund_occupancy(sh.l, sh.electrons)):
                if occ:
                    cnt = occ * ppe
                    pts = orbital_directions(sh.l, k, cnt, rng) * sample_radius(sh.n, sh.l, zeff, cnt, rng)[:, None]
                    pos.append(pts)
                    ns.append(np.full(cnt, sh.n))
                    ls.append(np.full(cnt, sh.l))
        else:
            cnt = sh.electrons * ppe
            pos.append(directions(cnt, rng) * sample_radius(sh.n, sh.l, zeff, cnt, rng)[:, None])
            ns.append(np.full(cnt, sh.n))
            ls.append(np.full(cnt, sh.l))
    return np.vstack(pos).astype(np.float32), np.concatenate(ns), np.concatenate(ls)


def probability_inside_nucleus(z: int, shells, radius_pm: float) -> float:
    """Probabilidad de encontrar a ALGÚN electrón dentro del núcleo (radio en pm).

    Solo cuentan los electrones s: son los únicos con densidad no nula en el centro,
    |ψ_ns(0)|² = Z_ef³ / (π n³ a₀³). Dentro de una esfera tan pequeña es casi constante:
        P ≈ (4/3) (Z_ef · R / a₀)³ / n³    por electrón.
    """
    x = radius_pm / BOHR_PM
    return sum(sh.electrons * 4 / 3 * (orbital_z(sh.n, 0, slater_zeff(z, shells, sh.n, 0)) * x) ** 3
               / sh.n ** 3 for sh in shells if sh.l == 0)


def sample_subshell(z: int, shells, index: int, per_electron: int, didactic: bool, rng=None,
                    only: int | None = None):
    """Puntos de un solo subnivel (o de uno de sus orbitales, `only`) para verlo de cerca.

    Devuelve (posiciones_pm (N,3), índice del orbital de cada punto (N,)). En modo realista
    la parte angular es esférica y el índice es siempre 0.
    """
    rng = rng or np.random.default_rng()
    sh = shells[index]
    zeff = orbital_z(sh.n, sh.l, slater_zeff(z, shells, sh.n, sh.l))
    if not didactic:
        cnt = sh.electrons * per_electron
        return directions(cnt, rng) * sample_radius(sh.n, sh.l, zeff, cnt, rng)[:, None], np.zeros(cnt, int)
    pos, owner = [], []
    for k, occ in enumerate(hund_occupancy(sh.l, sh.electrons)):
        if occ == 0 or (only is not None and k != only):
            continue
        cnt = occ * per_electron
        pos.append(orbital_directions(sh.l, k, cnt, rng) * sample_radius(sh.n, sh.l, zeff, cnt, rng)[:, None])
        owner.append(np.full(cnt, k))
    return np.vstack(pos), np.concatenate(owner)
