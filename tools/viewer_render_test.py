"""
Prueba del visor sin ventana: usa el autopiloto para bajar del átomo a los quarks y
guarda capturas PNG de cada nivel.

    python tools/viewer_render_test.py [carpeta_salida] [elemento] [isótopo] [idioma]
    python tools/viewer_render_test.py test_frames Fe 56 es
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import moderngl  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from atomicworld.repository import IsotopeTable, PeriodicTable  # noqa: E402
from ui.i18n import Translator  # noqa: E402
from viewer.engine import Engine  # noqa: E402
from viewer.hud import HUD  # noqa: E402

W, H = 1600, 900
DT = 1 / 60


def context():
    try:
        return moderngl.create_standalone_context()
    except Exception:
        return moderngl.create_standalone_context(backend="egl")


def main(out_dir="test_frames", element="Fe", mass_number=None, lang="es", didactic=True):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ctx = context()
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    table, isotopes = PeriodicTable(), IsotopeTable()
    el = table.find(element)
    iso = isotopes.get(el.number, int(mass_number)) if mass_number else isotopes.default(el)
    tr = Translator(lang)
    eng = Engine(ctx, el, iso, tr, didactic, isotopes.of(el.number))
    hud = HUD(ctx, tr)

    def snap(name):
        fbo.use()
        eng.render(W, H)
        hud.upload(hud.compose(eng.hud_state(W, H), W, H, eng.time))
        hud.draw()
        img = Image.frombytes("RGBA", (W, H), fbo.read(components=4)).transpose(
            Image.Transpose.FLIP_TOP_BOTTOM)
        img.convert("RGB").save(out / f"{name}.png")
        st = eng.hud_state(W, H)
        print(f"{name}: {eng.level.name!r} · dist={st['depth_m']:.2e} m · "
              f"foco={st['focus'].title if st['focus'] else None}")

    def run(frames, until=None):
        for _ in range(frames):
            eng.update(DT, np.zeros(3), False)
            while eng.messages:
                hud.flash(eng.messages.pop(0), eng.time, 3.0)
            if until and until():
                return True
        return False

    snap("0_atomo")
    eng.start_autopilot("down")
    run(240)
    snap("1_hacia_el_nucleo")
    assert run(3000, lambda: eng.autopilot is None), "el autopiloto no llegó al núcleo"
    run(30)
    snap("2_nucleo")
    eng.start_autopilot("down")
    assert run(3000, lambda: eng.autopilot is None), "el autopiloto no llegó al nucleón"
    run(40)
    snap("3_nucleon")
    eng.start_autopilot("down")
    assert run(3000, lambda: eng.autopilot is None), "el autopiloto no llegó al quark"
    snap("4_quark")
    eng.start_autopilot("up")
    assert run(3000, lambda: eng.autopilot is None)
    snap("5_subiendo_al_nucleo")
    eng.start_autopilot("up")
    assert run(4000, lambda: eng.autopilot is None)
    snap("6_de_vuelta_al_atomo")
    eng.toggle_mode()
    snap("7_atomo_realista")
    print("Capturas en", out.resolve())
    return eng


if __name__ == "__main__":
    main(*sys.argv[1:5])
