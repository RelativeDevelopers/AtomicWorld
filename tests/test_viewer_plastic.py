"""Tests del modo plástico del visor 3D: protones, neutrones, electrones y quarks como bolas."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atomicworld import atoms  # noqa: E402
from atomicworld.repository import IsotopeTable, PeriodicTable  # noqa: E402
from atomicworld.scene import orbitals  # noqa: E402
from ui.i18n import LANGUAGES, Translator  # noqa: E402

TABLE, ISOTOPES = PeriodicTable(), IsotopeTable()
MODES = ("didactic", "realistic", "plastic")


@pytest.mark.parametrize("language", LANGUAGES)
def test_plastic_texts_in_every_language(language):
    tr = Translator(language)
    for mode in MODES:
        for key in (f"viewer.hud.mode_{mode}", f"viewer.hud.now_{mode}"):
            assert tr.t(key) != key, key
    for key in ("viewer.atom.plastic", "viewer.nucleus.plastic", "viewer.nucleon.plastic"):
        assert tr.lines(key) != [key], key


def test_command_line_mode():
    from viewer.__main__ import parse_args
    assert parse_args(["O", "--mode", "plastic"]).mode == "plastic"
    with pytest.raises(SystemExit):
        parse_args(["O", "--mode", "cartoon"])


@pytest.mark.parametrize("symbol", ["H", "O", "Fe", "U"])
def test_one_orbit_per_electron(symbol):
    pytest.importorskip("moderngl")
    from viewer.levels import plastic
    el = TABLE.find(symbol)
    shells = atoms.subshells(el)
    o = plastic.electron_orbits(el.protons, shells, np.random.default_rng(0))
    assert o.count == el.electrons
    outer = max(orbitals.mean_radius_pm(s.n, s.l, atoms.slater_zeff(el.protons, shells, s.n, s.l))
                for s in shells)
    assert np.linalg.norm(o.positions(2.0), axis=1).max() <= outer * 1.08 + 1e-9


def test_particle_images_are_there():
    pytest.importorskip("moderngl")
    from PIL import Image
    from viewer.render import sprites
    for path in sprites.texture_paths():
        im = Image.open(path)
        assert im.mode == "RGBA" and im.size == (256, 256) and im.getpixel((0, 0))[3] == 0


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


def _fbo(ctx, w=320, h=180):
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 4)],
                          depth_attachment=ctx.depth_renderbuffer((w, h)))
    fbo.use()
    return fbo


def test_tab_cycles_through_the_modes(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("C")
    eng = Engine(gl_context, el, ISOTOPES.default(el), Translator("es"))
    _fbo(gl_context)
    seen = [eng.mode] + [eng.toggle_mode() for _ in range(3)]
    assert seen == ["didactic", "realistic", "plastic", "didactic"]
    assert eng.toggle_mode(-1) == "plastic" and eng.didactic
    eng.render(320, 180)
    assert eng.hud_state(320, 180)["mode"] == "plastic"


def test_plastic_atom_nucleus_and_quarks(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("O")
    iso = ISOTOPES.default(el)
    eng = Engine(gl_context, el, iso, Translator("en"), mode="plastic")
    _fbo(gl_context)
    root = eng.root
    assert root.balls.count == el.electrons + iso.a
    before = root.balls.positions[:el.electrons].copy()
    eng.update(0.5, np.zeros(3), False)
    assert not np.allclose(before, root.balls.positions[:el.electrons])

    def fly():
        eng.start_autopilot("down")
        for frame in range(6000):
            if eng.autopilot is None:
                return eng.level.depth
            eng.update(1 / 60, np.zeros(3), False)
            if frame % 300 == 0:
                eng.render(320, 180)
        raise AssertionError("autopilot did not finish")

    assert fly() == 1
    assert eng.level.balls.count == iso.a                     # 8 protons + 8 neutrons
    assert fly() == 2
    nucleon = eng.level
    assert nucleon.balls.count == 4                           # u, u, d (or u, d, d) + gluon
    assert fly() == 2                                         # end of the journey: a quark
    eng.render(320, 180)
    focus = eng.hud_state(320, 180)["focus"]
    assert focus is not None
    eng.toggle_mode()                                         # back to didactic: no balls
    assert eng.level.balls is None
    eng.render(320, 180)
