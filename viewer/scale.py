"""Formateo de longitudes, tiempos y semividas para el HUD, en el idioma elegido."""
import math
import re

_LENGTH_UNITS = [(1e-3, "mm"), (1e-6, "µm"), (1e-9, "nm"), (1e-12, "pm"),
                 (1e-15, "fm"), (1e-18, "am")]
_TIME_UNITS = [(1, "s"), (1e-3, "ms"), (1e-6, "µs"), (1e-9, "ns"), (1e-12, "ps"),
               (1e-15, "fs"), (1e-18, "as"), (1e-21, "zs"), (1e-24, "ys")]
YEAR_S = 365.25 * 86400


def _fmt(value: float, units, dec: str) -> str:
    if abs(value) < 1e-30:
        return "0 m" if units is _LENGTH_UNITS else "0 s"     # "0 m/s", no "0/s"
    for factor, name in units:
        if abs(value) >= factor * 0.999:
            v = value / factor
            txt = f"{v:.0f}" if v >= 100 else f"{v:.1f}" if v >= 10 else f"{v:.2f}"
            return txt.replace(".", dec) + " " + name
    factor, name = units[-1]
    return f"{value / factor:.3f}".replace(".", dec) + " " + name


def length(meters: float, dec: str = ".") -> str:
    """1.2e-10 -> '120 pm'"""
    return _fmt(meters, _LENGTH_UNITS, dec)


def duration(seconds: float, dec: str = ".") -> str:
    """Tiempos cortos con prefijos del SI: 3.5e-22 -> '0.350 zs'"""
    return _fmt(seconds, _TIME_UNITS, dec)


def half_life(seconds: float, tr) -> str:
    """Semivida legible: '12,3 s', '20 minutos', '5.700 años', '4,5×10⁹ años'."""
    def nice(v):
        return tr.num(v, 0) if v >= 100 else tr.num(v, 1) if v >= 10 else tr.num(v, 2)

    if seconds < 60:
        return duration(seconds, tr.dec)
    for unit, size, limit in (("minute", 60, 3600), ("hour", 3600, 86400), ("day", 86400, YEAR_S)):
        if seconds < limit:
            v = seconds / size
            return tr.t(f"units.{unit}.{'one' if round(v, 2) == 1 else 'other'}", n=nice(v))
    years = seconds / YEAR_S
    if years < 1e6:
        return tr.t(f"units.year.{'one' if round(years, 2) == 1 else 'other'}", n=nice(years))
    return tr.t("units.year.other", n=tr.sci(years))


_CLUSTER = re.compile(r"(\d+)([A-Z][a-z]?)")
_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def decay_mode(mode: str, tr) -> str:
    """Código de NUBASE -> texto: 'B-' -> 'β⁻', 'EC' -> 'captura electrónica', '14C' -> núcleo de ¹⁴C."""
    text = tr.t(f"viewer.decay.{mode}")
    if text != f"viewer.decay.{mode}":
        return text
    m = _CLUSTER.fullmatch(mode)
    if m:
        return tr.t("viewer.decay.cluster", nucleus=m.group(1).translate(_SUP) + m.group(2))
    # combinaciones como B-n, B+p, B+A: β⁻ + n
    pretty = (mode.replace("B-", "β⁻ + ").replace("B+", "β⁺ + ").replace("A", "α")
              .replace("SF", "fission").rstrip(" +"))
    return pretty


def isotope_summary(isotope, tr) -> str:
    """'estable', 'semivida 5.700 años · se desintegra por β⁻'..."""
    if isotope.is_stable:
        return tr.t("viewer.card.stable")
    parts = []
    if isotope.half_life_s:
        parts.append(tr.t("viewer.card.half_life", t=half_life(isotope.half_life_s, tr)))
    elif isotope.status == "radioactive":
        parts.append(tr.t("viewer.card.half_life_unknown"))
    else:
        parts.append(tr.t("viewer.card.unknown"))
    if isotope.decay:
        parts.append(decay_text(isotope, tr))
    return " · ".join(parts)


def decay_text(isotope, tr, limit: int = 2) -> str:
    """'se desintegra por β⁻ (89 %) o β⁺ (11 %)'"""
    items = []
    for m in isotope.decay[:limit]:
        label = decay_mode(m.mode, tr)
        if m.intensity is not None and m.intensity < 99.95 and len(isotope.decay) > 1:
            label += f" ({tr.num(m.intensity, 0)} %)"
        items.append(label)
    return tr.t("viewer.card.decay", modes=tr.t("viewer.decay.joiner").join(items))
