"""Abre el visor 3D en un proceso aparte: la consola sigue funcionando mientras tanto."""
import importlib.util
import subprocess
import sys
from pathlib import Path

from . import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIEWER_PACKAGES = ("numpy", "moderngl", "pyglet", "PIL")


def missing_dependencies() -> str:
    """Paquetes del visor que no están instalados ('' si no falta ninguno)."""
    return ", ".join(p for p in VIEWER_PACKAGES if importlib.util.find_spec(p) is None)


def viewer_command(element, isotope, lang: str | None = None) -> list[str]:
    return [sys.executable, "-m", "viewer", str(element.number), "--isotope", str(isotope.a),
            "--lang", lang or settings.language() or "en"]


def open_viewer(element, isotope, lang: str | None = None) -> subprocess.Popen:
    return subprocess.Popen(viewer_command(element, isotope, lang), cwd=PROJECT_ROOT)
