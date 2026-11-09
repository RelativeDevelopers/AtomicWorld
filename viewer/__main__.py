"""Arranca el visor 3D.

    python -m viewer Fe
    python -m viewer Hierro --isotope 54 --lang es
    python -m viewer 92 --isotope 235 --realistic
    python -m viewer O --mode plastic          (didactic, realistic, plastic)
"""
import argparse
import sys

from atomicworld.repository import IsotopeTable, PeriodicTable
from ui import settings
from ui.i18n import LANGUAGES, Translator


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="python -m viewer", description="AtomicWorld — 3D atom viewer")
    parser.add_argument("element", nargs="?", default="C",
                        help="name (any language), symbol or atomic number, e.g. Fe, Iron, Hierro, 26")
    parser.add_argument("--isotope", type=int, help="mass number, e.g. 14 for carbon-14")
    parser.add_argument("--lang", choices=LANGUAGES, help="en, es or ca (default: saved language)")
    parser.add_argument("--realistic", action="store_true", help="start in realistic mode")
    parser.add_argument("--mode", choices=("didactic", "realistic", "plastic"),
                        help="starting mode; plastic: protons, neutrons, electrons and quarks "
                             "as plastic balls")
    return parser.parse_args(argv)


def resolve(args, table, isotopes):
    """(elemento, isótopo) a partir de los argumentos; ValueError si no existen."""
    element = table.find(args.element)
    isotope = isotopes.get(element.number, args.isotope) if args.isotope else isotopes.default(element)
    return element, isotope


def main(argv=None):
    args = parse_args(argv)
    table, isotopes = PeriodicTable(), IsotopeTable()
    try:
        element, isotope = resolve(args, table, isotopes)
    except ValueError as exc:
        sys.exit(f"Error: {exc}")
    tr = Translator(args.lang or settings.language() or "en")

    import pyglet                       # solo aquí: los tests no necesitan ventana
    from viewer.app import App
    mode = args.mode or ("realistic" if args.realistic else "didactic")
    App(element, isotope, tr, didactic=not args.realistic, table=table, isotopes=isotopes, mode=mode)
    pyglet.app.run()


if __name__ == "__main__":
    main()
