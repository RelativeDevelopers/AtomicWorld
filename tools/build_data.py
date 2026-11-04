"""
Corrige atomicworld/data/elements.json y regenera particles.json con datos de referencia.

Uso (desde la carpeta raíz del proyecto):
    pip install mendeleev        # solo hace falta para este script, no para el programa
    python tools/build_data.py

Fuentes:
  - Elementos e isótopos: base de datos `mendeleev` (IUPAC/CIAAW para masas, NUBASE para isótopos).
  - Partículas: Particle Data Group, Review of Particle Physics 2024.
  - Masa del neutrino electrónico: KATRIN, Science 2025 (m < 0.45 eV, 90 % C.L.).

Qué hace con cada elemento:
  - atomic_mass   -> peso atómico estándar (o masa del isótopo más estable si no hay isótopos estables).
  - neutrons      -> neutrones del isótopo más ABUNDANTE en la naturaleza (o del más estable).
  - avg_neutrons  -> media ponderada por abundancia: lo que hay de verdad en una muestra real.
  - electron_config -> configuración electrónica del estado fundamental, p. ej. "[Ar] 3d6 4s2".
  - vdw_radius_pm -> radio de van der Waals (pm). Del 104 al 118 no se ha medido: se usa el del
                     elemento de su mismo grupo en el periodo 6 (Z − 32) y vdw_estimated = true.
  - color         -> color convencional de Jmol (no es un color real). Del 110 al 118, el del
                     elemento de su grupo en el periodo 6.
  - Puntos de fusión/ebullición: se corrigen solo los que se desvían claramente de la referencia.

Y genera isotopes.json con los ~3.500 isótopos conocidos (NUBASE, vía mendeleev).
"""
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from mendeleev.fetch import fetch_table  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "atomicworld" / "data"

# --- Correcciones explícitas de elementos -----------------------------------

MISSING_MERCURY = {
    "number": 80, "name": "Mercury", "symbol": "Hg", "atomic_mass": 200.592,
    "protons": 80, "neutrons": 122,
    "density_g_cm3": 13.534,           # líquido a temperatura ambiente
    "melting_c": -38.829, "boiling_c": 356.73,
}

FIXES = {
    # Renio: en el original era una copia del Rutenio.
    75: {"name": "Rhenium", "symbol": "Re", "density_g_cm3": 18.9,
         "melting_c": 3186, "boiling_c": 5596},
    # Puntos de fusión/ebullición que se desviaban de la referencia (°C).
    4: {"boiling_c": 2468},            # Berilio
    6: {"boiling_c": 3825, "melting_c": None},   # Carbono: sublima a 1 atm, no funde
    15: {"melting_c": 44.15},          # Fósforo blanco
    17: {"melting_c": -101.5},         # Cloro
    28: {"boiling_c": 2913},           # Níquel
    31: {"boiling_c": 2229},           # Galio
    41: {"boiling_c": 4744},           # Niobio
    69: {"boiling_c": 1950},           # Tulio
    77: {"boiling_c": 4428},           # Iridio
    79: {"boiling_c": 2856},           # Oro
    # Nombres IUPAC (las grafías americanas quedan como alias de búsqueda).
    13: {"name": "Aluminium", "aliases": ["Aluminum"]},
    55: {"name": "Caesium", "aliases": ["Cesium"]},
}

# --- Partículas (PDG 2024). Masas en MeV/c². --------------------------------
# Las masas de los quarks u, d, s son "masas corrientes" (esquema MS-bar a 2 GeV):
# no se pueden medir aisladas porque los quarks siempre están confinados.

PARTICLES = [
    # name,                    family,         mass_mev,     upper_limit, charge, spin, hypothetical
    ("Up",                     "Quark",        2.16,         False, "2/3",  "1/2", False),
    ("Charm",                  "Quark",        1273.0,       False, "2/3",  "1/2", False),
    ("Top",                    "Quark",        172570.0,     False, "2/3",  "1/2", False),
    ("Down",                   "Quark",        4.70,         False, "-1/3", "1/2", False),
    ("Strange",                "Quark",        93.5,         False, "-1/3", "1/2", False),
    ("Bottom",                 "Quark",        4183.0,       False, "-1/3", "1/2", False),
    ("Anti-up",                "Antiquark",    2.16,         False, "-2/3", "1/2", False),
    ("Anti-charm",             "Antiquark",    1273.0,       False, "-2/3", "1/2", False),
    ("Anti-top",               "Antiquark",    172570.0,     False, "-2/3", "1/2", False),
    ("Anti-down",              "Antiquark",    4.70,         False, "1/3",  "1/2", False),
    ("Anti-strange",           "Antiquark",    93.5,         False, "1/3",  "1/2", False),
    ("Anti-bottom",            "Antiquark",    4183.0,       False, "1/3",  "1/2", False),
    ("Electron",               "Lepton",       0.51099895,   False, "-1",   "1/2", False),
    ("Muon",                   "Lepton",       105.6583755,  False, "-1",   "1/2", False),
    ("Tau",                    "Lepton",       1776.93,      False, "-1",   "1/2", False),
    ("Electron neutrino",      "Lepton",       0.45e-6,      True,  "0",    "1/2", False),  # KATRIN 2025
    ("Muon neutrino",          "Lepton",       0.19,         True,  "0",    "1/2", False),
    ("Tau neutrino",           "Lepton",       18.2,         True,  "0",    "1/2", False),
    ("Positron",               "Antilepton",   0.51099895,   False, "1",    "1/2", False),
    ("Antimuon",               "Antilepton",   105.6583755,  False, "1",    "1/2", False),
    ("Antitau",                "Antilepton",   1776.93,      False, "1",    "1/2", False),
    ("Electron antineutrino",  "Antilepton",   0.45e-6,      True,  "0",    "1/2", False),
    ("Muon antineutrino",      "Antilepton",   0.19,         True,  "0",    "1/2", False),
    ("Tau antineutrino",       "Antilepton",   18.2,         True,  "0",    "1/2", False),
    ("Gluon",                  "Gauge Boson",  0.0,          False, "0",    "1",   False),
    ("Photon",                 "Gauge Boson",  0.0,          False, "0",    "1",   False),
    ("Z boson",                "Gauge Boson",  91187.6,      False, "0",    "1",   False),
    ("W+ boson",               "Gauge Boson",  80369.2,      False, "1",    "1",   False),
    ("W- boson",               "Gauge Boson",  80369.2,      False, "-1",   "1",   False),
    # El gravitón NO forma parte del Modelo Estándar: es hipotético y tendría espín 2.
    ("Graviton",               "Hypothetical", 0.0,          False, "0",    "2",   True),
    ("Higgs boson",            "Scalar Boson", 125200.0,     False, "0",    "0",   False),
]


def isotope_neutrons(iso, z: int, atomic_weight: float) -> tuple[int, float]:
    """(neutrones del isótopo más abundante, media ponderada por abundancia)."""
    natural = iso[(iso.atomic_number == z) & iso.abundance.notna() & (iso.abundance > 0)]
    if len(natural):
        top = natural.sort_values("abundance").iloc[-1]
        n_main = int(top.mass_number) - z
        total = natural.abundance.sum()
        avg = float(((natural.mass_number - z) * natural.abundance).sum() / total)
        return n_main, round(avg, 4)
    # Sin isótopos naturales: el peso atómico tabulado es el número másico del más estable.
    n = round(atomic_weight) - z
    return n, float(n)


# Elementos superpesados sin datos: se toma el del mismo grupo en el periodo 6 (Z − 32).
HOMOLOGUE_OFFSET = 32


def _clean_config(text: str) -> str:
    """'[Ar] 3d5 4s' -> '[Ar] 3d5 4s1': mendeleev omite el 1."""
    parts = []
    for part in text.split():
        if part.startswith("["):
            parts.append(part)
        else:
            parts.append(part if part[-1].isdigit() and len(part) > 2 else part + "1")
    return " ".join(parts)


def _homologue_value(ref, z: int, column: str):
    """Valor de la columna para z; si falta, el del homólogo del periodo 6 (y si es estimado)."""
    value = ref.loc[z, column]
    if value == value and value is not None:       # no es NaN
        return value, False
    return ref.loc[z - HOMOLOGUE_OFFSET, column], True


def build_elements() -> list[dict]:
    ref = fetch_table("elements").set_index("atomic_number")
    iso = fetch_table("isotopes")

    current = json.loads((DATA / "elements.json").read_text(encoding="utf-8"))
    by_z = {e["number"]: e for e in current}
    by_z.setdefault(80, MISSING_MERCURY)

    out = []
    for z in range(1, 119):
        e = dict(by_z[z])
        e.update(FIXES.get(z, {}))
        r = ref.loc[z]
        e["symbol"] = r.symbol
        e["atomic_mass"] = round(float(r.atomic_weight), 6)
        e["protons"] = z
        e["neutrons"], e["avg_neutrons"] = isotope_neutrons(iso, z, float(r.atomic_weight))
        e.setdefault("aliases", [])
        e["electron_config"] = _clean_config(r.electronic_configuration)
        vdw, e["vdw_estimated"] = _homologue_value(ref, z, "vdw_radius")
        e["vdw_radius_pm"] = round(float(vdw), 1)
        e["color"], _ = _homologue_value(ref, z, "jmol_color")
        out.append({k: e.get(k) for k in (
            "number", "name", "symbol", "aliases", "atomic_mass", "protons", "neutrons",
            "avg_neutrons", "density_g_cm3", "melting_c", "boiling_c",
            "electron_config", "vdw_radius_pm", "vdw_estimated", "color")})
    return out


# --- Isótopos ------------------------------------------------------------------

YEAR_S = 365.25 * 86400       # año juliano, el que usa NUBASE
HALF_LIFE_UNITS = {
    "ysec": 1e-24, "zsec": 1e-21, "asec": 1e-18, "psec": 1e-12, "nsec": 1e-9, "usec": 1e-6,
    "msec": 1e-3, "sec": 1.0, "minute": 60.0, "hour": 3600.0, "day": 86400.0,
    "year": YEAR_S, "kyear": 1e3 * YEAR_S, "Myear": 1e6 * YEAR_S, "Gyear": 1e9 * YEAR_S,
    "Tyear": 1e12 * YEAR_S, "Pyear": 1e15 * YEAR_S, "Eyear": 1e18 * YEAR_S,
    "Zyear": 1e21 * YEAR_S, "Yyear": 1e24 * YEAR_S,
}


def _nan_to_none(value):
    return None if value != value else value       # NaN != NaN


def _decay_modes(rows) -> list[dict]:
    """Modos de desintegración en el orden de NUBASE (el primero es el principal).

    En mendeleev las intensidades de los modos raros pierden el exponente (la fisión del U-235
    sale como 7 % en vez de 7·10⁻⁹ %). Solo se guardan si todas suman ~100 %, como en el K-40
    (89 % β⁻ + 11 % β⁺); si no, solo se guarda la del modo principal.
    Se descartan los modos permitidos pero nunca observados (p. ej. la doble β⁺ del Ar-36,
    que en la práctica es estable).
    """
    rows = rows[rows.is_allowed_not_observed != 1]
    modes = [{"mode": r.mode.strip(),
              "intensity": float(r.intensity) if r.relation == "=" and r.intensity == r.intensity else None}
             for r in rows.itertuples()]
    known = [m["intensity"] for m in modes if m["intensity"] is not None]
    if not (known and abs(sum(known) - 100) < 0.5 and len(known) == len(modes)):
        for m in modes[1:]:
            m["intensity"] = None
    return modes


def build_isotopes() -> list[dict]:
    iso = fetch_table("isotopes")
    decays = fetch_table("isotopedecaymodes").sort_values("id")
    by_isotope = dict(tuple(decays.groupby("isotope_id")))
    out = []
    for r in iso.sort_values(["atomic_number", "mass_number"]).itertuples():
        abundance = _nan_to_none(r.abundance)
        half_life = None
        if r.half_life == r.half_life and r.half_life_unit in HALF_LIFE_UNITS:
            half_life = float(f"{r.half_life * HALF_LIFE_UNITS[r.half_life_unit]:.6g}")
        if r.is_radioactive:
            status = "radioactive"
        elif abundance:
            status = "stable"
        else:
            status = "unknown"     # no ligados o sin medir (p. ej. C-21)
        rows = by_isotope.get(r.id)
        out.append({
            "z": int(r.atomic_number), "a": int(r.mass_number),
            "mass_u": float(r.mass),
            "abundance": float(abundance) if abundance else None,     # % en la naturaleza
            "status": status,
            "half_life_s": half_life,
            "decay": _decay_modes(rows) if rows is not None else [],
            "spin": _nan_to_none(r.spin),
            "parity": _nan_to_none(r.parity),
        })
    return out


def write_one_per_line(path: Path, rows: list[dict]) -> None:
    """Un registro por línea: el archivo pesa la mitad y los cambios se leen bien en git."""
    lines = ",\n  ".join(json.dumps(r, ensure_ascii=False) for r in rows)
    path.write_text(f"[\n  {lines}\n]\n", encoding="utf-8")


def build_particles() -> list[dict]:
    old = json.loads((DATA / "particles.json").read_text(encoding="utf-8"))
    binaries = [p["binary"] for p in old]          # se conservan los códigos del original
    assert len(binaries) == len(PARTICLES)
    return [
        {"name": n, "family": f, "mass_mev": m, "mass_is_upper_limit": ul,
         "charge": q, "spin": s, "hypothetical": h, "binary": b}
        for (n, f, m, ul, q, s, h), b in zip(PARTICLES, binaries)
    ]


def main() -> None:
    elements = build_elements()
    particles = build_particles()
    for name, content in (("elements.json", elements), ("particles.json", particles)):
        (DATA / name).write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
        print(f"  {name}: {len(content)} registros")
    isotopes = build_isotopes()
    write_one_per_line(DATA / "isotopes.json", isotopes)
    print(f"  isotopes.json: {len(isotopes)} registros")


if __name__ == "__main__":
    main()
