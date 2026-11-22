"""
El estándar de controles de los visores 3D de Relative Developers.

Los cuatro visores (Átomo en 3D de AtomicWorld; Microscopio 3D, Proteína 3D y Cuerpo humano de
DNAinvent) usan las mismas teclas, el mismo ratón y los mismos gestos, en la consola (pyglet) y
en la web. La tabla está en un solo sitio, web_assets/controls.json: la leen este módulo (para los
visores de escritorio) y v3d-controls.js (para las webs, que la llevan copiada y un test comprueba
que es idéntica). La explicación para personas está en docs/CONTROLES.md.

Regla: una tecla = una sola acción en los cuatro visores. Si un visor no tiene esa función, la
tecla no hace otra cosa: el visor avisa de que no está disponible ahí.

Uso en un visor de pyglet:

    keymap = controls.KeyMap("microscope")
    keymap.axis(keys, "forward", "back")           # teclas mantenidas: -1, 0 o 1
    action = keymap.action(symbol, modifiers)      # tecla pulsada: "go", "go_full", "light"…
    if action and not keymap.available(action): …  # «no disponible aquí»

No importa pyglet hasta que se usa KeyMap: el núcleo no depende de pyglet.
"""
import json
from functools import lru_cache
from importlib import resources

VIEWERS = ("atom3d", "microscope", "protein3d", "body")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(resources.files("atomicworld.web_assets").joinpath("controls.json").read_text("utf-8"))


def actions(viewer: str) -> set[str]:
    """Las acciones que tiene un visor: las comunes y las suyas (con sus variantes con Mayús)."""
    data = load()
    if viewer not in data["viewers"]:
        raise ValueError(f"unknown viewer: {viewer}")
    names = set(data["common"]) | set(data["viewers"][viewer])
    return names | {alt for base, alt in data["shift"].items() if base in names}


def all_keys() -> list[tuple[str, str]]:
    """[(tecla, acción)] de toda la tabla: sirve para comprobar que ninguna tecla se repite."""
    data = load()
    out = []
    for group in ("held", "press"):
        for action, keys in data[group].items():
            out += [(k["text"] if isinstance(k, dict) else k, action) for k in keys]
    return out


def _pyglet_symbols(code: str) -> tuple:
    from pyglet.window import key
    special = {
        "Space": (key.SPACE,), "Enter": (key.ENTER, key.RETURN), "NumpadEnter": (key.NUM_ENTER,),
        "Backspace": (key.BACKSPACE,), "Escape": (key.ESCAPE,), "F11": (key.F11,),
        "ArrowLeft": (key.LEFT,), "ArrowRight": (key.RIGHT,), "ArrowUp": (key.UP,), "ArrowDown": (key.DOWN,),
        "ShiftLeft": (key.LSHIFT,), "ShiftRight": (key.RSHIFT,),
    }
    if code in special:
        return special[code]
    if code.startswith("Key") and len(code) == 4:
        return (getattr(key, code[3]),)
    raise ValueError(f"unknown key code: {code}")


class KeyMap:
    """Las teclas del estándar traducidas a pyglet, para un visor concreto."""

    def __init__(self, viewer: str):
        from pyglet.window import key
        self.viewer = viewer
        self.available_actions = actions(viewer)
        data = load()
        self._shift_mask = key.MOD_SHIFT
        self._held = {a: tuple(s for c in codes for s in _pyglet_symbols(c)) for a, codes in data["held"].items()}
        self._press, self._text = {}, {}
        for action, codes in data["press"].items():
            for c in codes:
                if isinstance(c, dict):
                    self._text[c["text"]] = action
                else:
                    for s in _pyglet_symbols(c):
                        self._press[s] = action
        self._shift = data["shift"]

    def available(self, action: str) -> bool:
        return action in self.available_actions

    def held(self, state, action: str) -> bool:
        """¿Está pulsada alguna tecla de esa acción? state: pyglet KeyStateHandler."""
        return any(state[s] for s in self._held[action])

    def axis(self, state, plus: str, minus: str) -> int:
        return int(self.held(state, plus)) - int(self.held(state, minus))

    def is_held_key(self, symbol) -> bool:
        return any(symbol in syms for syms in self._held.values())

    def action(self, symbol, modifiers=0) -> str | None:
        """La acción de una tecla pulsada (con Mayús, su variante: Mayús+Enter = go_full)."""
        action = self._press.get(symbol)
        if action and modifiers & self._shift_mask and action in self._shift:
            return self._shift[action]
        return action

    def text_action(self, text: str) -> str | None:
        """Las teclas que se leen como carácter ([ y ]), para on_text."""
        return self._text.get(text)
