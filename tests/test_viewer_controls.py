"""Átomo en 3D (escritorio) con el estándar común de controles (docs/CONTROLES.md)."""
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from atomicworld.repository import IsotopeTable, PeriodicTable  # noqa: E402
from ui.i18n import Translator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLE, ISOTOPES = PeriodicTable(), IsotopeTable()


@pytest.fixture(scope="module")
def gl_context():
    moderngl = pytest.importorskip("moderngl")
    for backend in (None, "egl"):
        try:
            return moderngl.create_standalone_context(backend=backend) if backend \
                else moderngl.create_standalone_context()
        except Exception:
            continue
    pytest.skip("no OpenGL context available")


@pytest.fixture()
def engine(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("C")
    return Engine(gl_context, el, ISOTOPES.default(el), Translator("es"))


def test_wheel_and_pinch_get_closer(engine):
    d0 = engine.surface_distance()
    engine.zoom_by(1.15)
    assert engine.surface_distance() == pytest.approx(d0 / 1.15, rel=0.02)
    engine.zoom_by(1 / 1.15)
    assert engine.surface_distance() == pytest.approx(d0, rel=0.02)


def test_a_jump_never_goes_through_the_object(engine):
    d0 = engine.surface_distance()
    engine.zoom_by(1000)                           # un salto enorme se limita al 60 % de la distancia
    assert engine.surface_distance() == pytest.approx(0.4 * d0, rel=0.05)


def test_pan_follows_the_mouse(engine):
    s = engine.ship
    p0, right, up = s.pos.copy(), s.right.copy(), s.up.copy()
    engine.pan_by(40, 0, 900)                      # el ratón va a la derecha: la nave, a la izquierda
    assert (s.pos - p0) @ right < 0
    p1 = s.pos.copy()
    engine.pan_by(0, -40, 900)                     # el ratón sube: la nave baja (la escena sube)
    assert (s.pos - p1) @ up < 0


def test_reset_view(engine):
    start = engine.ship.pos.copy()
    engine.zoom_by(3)
    engine.ship.look(200, 50)
    engine.reset_view()
    assert np.allclose(engine.ship.pos, start) and len(engine.stack) == 1 and engine.autopilot is None


def test_all_the_way_down(engine):
    engine.start_autopilot("down", full=True)
    for _ in range(3000):
        engine.update(1 / 60, np.zeros(3), False)
        if engine.autopilot is None:
            break
    assert engine.level.depth == 2                 # dentro de un nucleón, hasta los quarks
    assert any("quark" in m for m in engine.messages)


def test_light_background_pass(gl_context):
    from atomicworld.v3d_desktop import LightBackground
    fbo = gl_context.framebuffer(color_attachments=[gl_context.texture((64, 32), 4)])
    fbo.use()
    light = LightBackground(gl_context, samples=0)
    with light.scene(64, 32):
        gl_context.clear(0.0, 0.0, 0.0, 1.0)       # el espacio negro…
    pixel = np.frombuffer(fbo.read(components=3), dtype=np.uint8)[:3]
    assert (pixel > 250).all()                     # …sale blanco


def test_app_follows_the_standard():
    source = (ROOT / "viewer" / "app.py").read_text(encoding="utf-8")
    assert 'controls.KeyMap("atom3d")' in source
    for old in ("set_exclusive_mouse", "key.TAB", "key.LCTRL", "next_language", "speed_mult *"):
        assert old not in source, old
    from atomicworld import controls
    handled = set()
    for line in source.split("def do_action")[1].splitlines():
        handled |= {a for a in controls.actions("atom3d") if f'"{a}"' in line}
    held = set(controls.load()["held"])
    assert handled - held == controls.actions("atom3d") - held
