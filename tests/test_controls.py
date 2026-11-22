"""El estándar de controles de los cuatro visores 3D (atomicworld/web_assets/controls.json)."""
import json
import re
from collections import Counter

import pytest

from atomicworld import controls
from atomicworld.web_assets import ASSETS_DIR


def test_one_key_one_action():
    # La regla del estándar: ninguna tecla hace dos cosas, en ningún visor
    repeated = [k for k, n in Counter(k for k, _ in controls.all_keys()).items() if n > 1]
    assert not repeated


def test_every_listed_action_exists():
    data = controls.load()
    defined = set(data["held"]) | set(data["press"]) | set(data["shift"].values())
    for name in data["common"] + [a for own in data["viewers"].values() for a in own]:
        assert name in defined, name
    assert set(data["shift"]) <= set(data["press"])


def test_unique_actions_belong_to_some_viewer():
    data = controls.load()
    used = set(data["common"]) | {a for own in data["viewers"].values() for a in own}
    assert set(data["press"]) | set(data["held"]) <= used


def test_buttons_are_actions_of_their_viewer():
    data = controls.load()
    for viewer, rows in data["buttons"].items():
        if viewer == "about":
            continue
        assert all(len(row) == 3 for row in rows), viewer
        assert rows[-1] == ["more", "help", "fullscreen"], viewer            # la última fila, igual en todos
        assert rows[1][1:] == ["light", "reset"], viewer                     # «cómo se ve», igual en todos
        mine = controls.actions(viewer)
        assert all(a in mine for row in rows for a in row if a is not None), viewer


def test_the_web_copy_is_identical():
    # v3d-controls.js lleva una copia del estándar: no puede separarse de controls.json
    js = (ASSETS_DIR / "v3d-controls.js").read_text(encoding="utf-8")
    copy = re.search(r"// BEGIN STANDARD.*?\n\s*const STANDARD = (\{.*?\});\n\s*// END STANDARD", js, re.S).group(1)
    assert json.loads(copy) == controls.load()


def test_protein3d_is_the_microscope():
    data = controls.load()
    assert data["viewers"]["protein3d"] == data["viewers"]["microscope"]


def test_unknown_viewer():
    with pytest.raises(ValueError):
        controls.actions("telescope")


def _pyglet_key():
    """pyglet.window necesita una pantalla (o EGL): sin ella, estos tests se saltan."""
    try:
        from pyglet.window import key
    except Exception as error:                     # sin pyglet o sin pantalla
        pytest.skip(f"pyglet no disponible aquí: {error.__class__.__name__}")
    return key


def test_pyglet_keymap():
    key = _pyglet_key()
    keymap = controls.KeyMap("atom3d")
    assert keymap.action(key.ENTER) == "go"
    assert keymap.action(key.RETURN, key.MOD_SHIFT) == "go_full"
    assert keymap.action(key.M, key.MOD_SHIFT) == "mode_back"
    assert keymap.action(key.B) == "light"
    assert keymap.action(key.L) == "more"                  # L ya no es el idioma
    assert keymap.action(key.TAB) is None                  # ni Tab el modo
    assert keymap.text_action("[") == "previous_isotope"
    assert keymap.is_held_key(key.C) and keymap.is_held_key(key.LEFT)
    assert keymap.available("next_element") and not keymap.available("isolate")
    body = controls.KeyMap("body")
    assert body.action(key.X) == "isolate" and body.available("isolate")
    assert not body.available("subshell")


def test_every_key_code_maps_to_pyglet():
    _pyglet_key()
    for code, _ in controls.all_keys():
        if len(code) > 1:                                  # los caracteres ([ ]) van por on_text
            assert controls._pyglet_symbols(code)


def test_light_background_is_the_same_everywhere():
    """La matriz del fondo claro (invert + hue-rotate 180° de CSS) es la misma en la web y en el
    escritorio, y es su propia inversa: lo que se dibuja ya invertido vuelve a su color."""
    import numpy as np
    from atomicworld.v3d_desktop import LIGHT_GLSL
    pattern = r"mat3\(([^)]*)\)"
    sources = [LIGHT_GLSL, (ASSETS_DIR / "v3d-controls.js").read_text(encoding="utf-8"),
               (ASSETS_DIR / "v3d-plastic.js").read_text(encoding="utf-8")]
    matrices = [re.search(pattern, s).group(1).split(",") for s in sources]
    assert matrices[0] == matrices[1] == matrices[2]
    columns = np.array([float(x) for x in matrices[0]]).reshape(3, 3)
    h = columns.T                                       # GLSL: por columnas
    assert np.allclose(h @ h, np.eye(3), atol=2e-3)
    assert np.allclose(h @ np.ones(3), np.ones(3), atol=2e-3)   # el blanco sigue siendo blanco
    assert "invert(1) hue-rotate(180deg)" in (ASSETS_DIR / "v3d-ui.css").read_text(encoding="utf-8")
