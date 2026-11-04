"""
Convierte las tablas `elements` y `subelements` del script original
(legacy/AtomicWorld_original.py) a los archivos JSON del paquete.

Uso (desde la carpeta raíz del proyecto):
    python tools/convert_legacy.py

La conversión es FIEL al original: no corrige ningún dato. Las correcciones
se hacen después directamente en los JSON.
"""
import ast
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "legacy" / "AtomicWorld_original.py"
DATA_DIR = ROOT / "atomicworld" / "data"


def read_legacy_lists(path: Path) -> dict:
    """Lee las asignaciones `elements = [...]` y `subelements = [...]` sin
    ejecutar el resto del script (que tiene un bucle con input())."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    wanted = {"elements", "subelements"}
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                # eval en un entorno vacío: las listas solo tienen literales
                # y divisiones como 2/3, así que no necesitan nada más.
                code = compile(ast.Expression(node.value), str(path), "eval")
                found[target.id] = eval(code, {"__builtins__": {}}, {})
    missing = wanted - found.keys()
    if missing:
        raise RuntimeError(f"No se encontraron en el original: {missing}")
    return found


def as_fraction_text(value: float) -> str:
    """0.6666... -> '2/3', 1 -> '1'"""
    return str(Fraction(value).limit_denominator(3))


def convert_elements(raw: list[dict]) -> list[dict]:
    out = []
    for e in raw:
        density = next((v for k, v in e.items() if k.startswith("Density")), None)
        out.append({
            # El número atómico ES el número de protones. Así no dependemos
            # de la posición en la lista (el origen del desfase del Mercurio).
            "number": e["Protons"],
            "name": e["Name"],
            "symbol": e["Symbol"],
            "atomic_mass": e["Atomic mass (u)"],
            "protons": e["Protons"],
            "neutrons": e["Neutrons"],
            "density_g_cm3": density,
            "melting_c": e.get("Melting (°C)"),
            "boiling_c": e.get("Boiling (°C)"),
        })
    return out


def convert_particles(raw: list[dict]) -> list[dict]:
    out = []
    last_family = None
    for p in raw:
        if "mass MeVC2" in p:
            mass_mev = p["mass MeVC2"]
        else:
            mass_mev = p["mass GeVC2"] * 1000  # GeV -> MeV
        family = p.get("Family")
        if family is None:
            family = last_family
            print(f"  Aviso: '{p['Name']}' no tenía 'Family'; se asigna '{family}'.")
        last_family = family
        out.append({
            "name": p["Name"],
            "family": family,
            "mass_mev": mass_mev,
            "charge": as_fraction_text(p["charge"]),
            "spin": as_fraction_text(p["spin"]),
            "binary": p["Binary"],
        })
    return out


def main() -> None:
    data = read_legacy_lists(LEGACY)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    elements = convert_elements(data["elements"])
    particles = convert_particles(data["subelements"])

    for filename, content in (("elements.json", elements), ("particles.json", particles)):
        target = DATA_DIR / filename
        target.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {target.relative_to(ROOT)}: {len(content)} registros")


if __name__ == "__main__":
    main()
