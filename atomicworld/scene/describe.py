"""Resumen de un átomo para el visor web: todo lo que necesita para dibujarlo, en tablas pequeñas.

El visor de escritorio genera los puntos aquí mismo, con NumPy. El web los genera en el
navegador, pero sin física: recibe, por ejemplo, la tabla de radios de cada subnivel
(radius_quantiles) y solo tiene que interpolar. Así la física está en un solo sitio.

    describe_atom(table.find("Fe"), isotopes.get(26, 56))   # -> dict listo para JSON (~30 kB)
"""
from functools import lru_cache

import numpy as np

from .. import atoms
from ..constants import NEUTRON_MASS_MEV, PROTON_MASS_MEV
from ..repository import IsotopeTable, ParticleCatalog
from . import nucleus as nuc
from . import orbitals

QUANTILES = 257          # puntos de cada tabla de radios


def _round(values, digits=4):
    """Menos decimales = JSON más pequeño (4 cifras significativas sobran para dibujar)."""
    return [float(f"{v:.{digits}g}") for v in np.asarray(values).ravel()]


def isotope_dict(iso) -> dict:
    return {
        "a": iso.a, "neutrons": iso.neutrons, "mass_u": iso.mass_u, "abundance": iso.abundance,
        "status": iso.status, "half_life_s": iso.half_life_s,
        "decay": [{"mode": m.mode, "intensity": m.intensity} for m in iso.decay],
    }


def describe_atom(element, isotope, isotopes: IsotopeTable | None = None,
                  particles: ParticleCatalog | None = None) -> dict:
    isotopes = isotopes or IsotopeTable()
    particles = particles or ParticleCatalog()
    shells = atoms.subshells(element)
    z = element.protons
    style = orbitals.didactic_style(z, shells)
    ppe = orbitals.didactic_points(z, shells)
    a_count = isotope.a
    radius_fm = atoms.nuclear_radius_fm(a_count)
    rng = np.random.default_rng(element.number * 1000 + a_count)   # mismo núcleo que en escritorio
    centers = nuc.pack_nucleons(a_count, radius_fm, rng)
    kinds = nuc.assign_kinds(element.protons, isotope.neutrons, rng)
    ws_r = np.linspace(0, radius_fm + 10 * nuc.WS_DIFFUSENESS_FM, 4000)
    ws_cdf = np.cumsum(ws_r ** 2 / (1 + np.exp((ws_r - radius_fm) / nuc.WS_DIFFUSENESS_FM)))
    ws_cdf /= ws_cdf[-1]

    subshells = []
    for s in shells:
        zeff = atoms.slater_zeff(z, shells, s.n, s.l)
        alpha, size = style[(s.n, s.l)]
        subshells.append({
            "n": s.n, "l": s.l, "name": s.name, "label": s.label, "electrons": s.electrons,
            "zeff": round(zeff, 4),
            "mean_radius_pm": round(orbitals.mean_radius_pm(s.n, s.l, zeff), 3),
            "occupancy": orbitals.hund_occupancy(s.l, s.electrons),
            "orbitals": orbitals.orbital_names(s.l),
            "radius_quantiles_pm": _round(orbitals.radius_quantiles(s.n, s.l, zeff, QUANTILES)),
            "didactic": {"points_per_electron": ppe[(s.n, s.l)], "alpha": round(alpha, 4), "size_pm": round(size, 3)},
        })
    return {
        "element": {"number": element.number, "symbol": element.symbol, "protons": z,
                    "electrons": element.electrons, "vdw_radius_pm": element.vdw_radius_pm,
                    "color": element.color},
        "isotope": isotope_dict(isotope),
        "isotopes": [{"a": i.a, "abundance": i.abundance} for i in isotopes.of(element.number)],
        "atom": {
            "subshells": subshells,
            "view_distance_pm": round(orbitals.atom_view_distance(element.vdw_radius_pm, z, shells), 2),
            "nucleus_radius_pm": radius_fm / 1000,
            "realistic_points_per_electron": orbitals.points_per_electron(element.electrons),
        },
        "nucleus": {
            "radius_fm": radius_fm,
            "centers_fm": [_round(c, 5) for c in centers],
            "kinds": "".join(kinds),
            "density_kg_m3": nuc.density_kg_m3(a_count, radius_fm),
            "electron_inside_probability": orbitals.probability_inside_nucleus(z, shells, radius_fm / 1000),
            "points_per_nucleon": nuc.points_per_nucleon(a_count),
            "nucleon_a_fm": nuc.NUCLEON_A_FM,
            "woods_saxon_quantiles_fm": _round(np.interp(np.linspace(0, 1, QUANTILES), ws_cdf, ws_r)),
        },
        "masses_mev": {"proton": PROTON_MASS_MEV, "neutron": NEUTRON_MASS_MEV,
                       "up": particles.find("Up").mass_mev, "down": particles.find("Down").mass_mev},
    }


@lru_cache(maxsize=64)
def describe_cached(z: int, a: int) -> dict:
    """Para servidores: el mismo átomo no se vuelve a calcular (empaquetar 294 nucleones ~1 s)."""
    element = next(e for e in _table() if e.number == z)
    return describe_atom(element, _isotopes().get(z, a), _isotopes(), _particles())


@lru_cache(maxsize=1)
def _table():
    from ..repository import PeriodicTable
    return PeriodicTable()


@lru_cache(maxsize=1)
def _isotopes():
    return IsotopeTable()


@lru_cache(maxsize=1)
def _particles():
    return ParticleCatalog()
