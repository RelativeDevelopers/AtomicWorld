"""Preferencias del usuario guardadas entre sesiones (por ahora, el idioma).

Se guardan en ~/.atomicworld/settings.json. Si el archivo no existe o está roto,
se usan los valores por defecto: nunca impide arrancar el programa.
"""
import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".atomicworld" / "settings.json"


def load(path: Path | None = None) -> dict:
    path = path or SETTINGS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(values: dict, path: Path | None = None) -> None:
    path = path or SETTINGS_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**load(path), **values}, indent=2), encoding="utf-8")
    except OSError:
        pass           # sin permisos de escritura: se pregunta otra vez la próxima vez


def language(path: Path | None = None) -> str | None:
    return load(path).get("language")
