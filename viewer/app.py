"""
La ventana del visor: controles, bucle y teclas.

Los controles siguen el estándar común de los visores 3D (atomicworld/web_assets/controls.json,
docs/CONTROLES.md): las mismas teclas que la web y que los visores de DNAinvent.

    python -m viewer Fe                       (hierro, isótopo más abundante)
    python -m viewer Uranio --isotope 235     (cualquier idioma, símbolo o número atómico)
    python -m viewer 6 --isotope 14 --lang ca --realistic
"""
import time

import moderngl
import numpy as np
import pyglet
from pyglet.window import key, mouse

from atomicworld import controls
from atomicworld.repository import IsotopeTable, PeriodicTable
from ui import settings
from viewer.engine import Engine
from viewer.hud import HUD


class App(pyglet.window.Window):
    def __init__(self, element, isotope, tr, didactic=True, table=None, isotopes=None, mode=None):
        self.tr = tr
        self.table = table or PeriodicTable()
        self.isotopes = isotopes or IsotopeTable()
        # depth_size: el modo plástico usa el búfer de profundidad (las bolas se tapan)
        config = pyglet.gl.Config(double_buffer=True, major_version=3, minor_version=3,
                                  forward_compatible=True, sample_buffers=1, samples=4,
                                  depth_size=24)
        try:
            super().__init__(1600, 900, tr.t("viewer.title"), resizable=True, config=config)
        except pyglet.window.NoSuchConfigException:
            super().__init__(1600, 900, tr.t("viewer.title"), resizable=True)
        self.ctx = moderngl.create_context()
        print("GPU:", self.ctx.info["GL_RENDERER"])
        if "Intel" in self.ctx.info["GL_RENDERER"]:
            print("WARNING: using the integrated graphics card. On Windows, choose the NVIDIA one in "
                  "Settings > System > Display > Graphics.")

        self.engine = Engine(self.ctx, element, isotope, tr, didactic, self.isotopes.of(element.number),
                             mode)
        self.hud = HUD(self.ctx, tr)
        self.hud_timer = 0.0
        self.pending = None               # cambio de átomo que se hace en el siguiente frame
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.keymap = controls.KeyMap("atom3d")
        self.light_pass = None            # fondo claro: se crea la primera vez que se usa
        self.set_light(bool(settings.load().get("light")), save=False)
        self._press = None                # (x, y, botón) al pulsar el ratón: clic o arrastre
        self._last_click = (0.0, 0, 0)    # para el doble clic
        self.hud.flash(tr.t("viewer.hud.start"), 0.0, 4.0)
        pyglet.clock.schedule_interval(self.tick, 1 / 144)

    # ------------------------------------------------------------ bucle
    def tick(self, dt):
        if self.pending:                   # se ejecuta después de haber dibujado el aviso
            action, self.pending = self.pending, None
            action()
            dt = 1 / 60
        dt = min(dt, 0.05)
        k, km = self.keys, self.keymap
        move = np.array([km.axis(k, "right", "left"), km.axis(k, "up", "down"), km.axis(k, "forward", "back")], dtype=float)
        turbo = km.held(k, "turbo")
        roll = km.axis(k, "roll_left", "roll_right")
        if roll:
            self.engine.ship.roll(roll * 1.2 * dt)
        look_x, look_y = km.axis(k, "look_right", "look_left"), km.axis(k, "look_up", "look_down")
        if look_x or look_y:                       # flechas: mover la cámara (→ = mirar a la derecha)
            turn = 420 * dt * (3 if turbo else 1)
            self.engine.ship.look(look_x * turn, look_y * turn)
            self.engine.autopilot = None
        self.engine.ship.speed_mult = 1.0
        prev_level = self.engine.level
        self.engine.update(dt, move, turbo)
        if self.engine.level is not prev_level:
            entering = self.engine.level.depth > prev_level.depth
            text = "viewer.hud.entering" if entering else "viewer.hud.leaving"
            self.hud.flash(self.tr.t(text, name=self.engine.level.name), self.engine.time)
        while self.engine.messages:
            self.hud.flash(self.engine.messages.pop(0), self.engine.time, 3.0)
        self.hud_timer -= dt
        if self.hud_timer <= 0:
            self.refresh_hud()

    def refresh_hud(self):
        self.hud_timer = 0.12
        w, h = self.get_framebuffer_size()
        state = self.engine.hud_state(w, h)
        state["speed_mult"] = 5.0 if self.keymap.held(self.keys, "turbo") else 1.0
        self.hud.upload(self.hud.compose(state, w, h, self.engine.time))

    def on_draw(self):
        w, h = self.get_framebuffer_size()
        self.ctx.screen.use()
        if self.light:
            with self.light_pass.scene(w, h):      # la escena se invierte al pasar a la pantalla
                self.engine.render(w, h)
        else:
            self.engine.render(w, h)
        self.hud.draw()

    def set_light(self, on: bool, save: bool = True):
        """B: fondo claro u oscuro (se recuerda en ~/.atomicworld/settings.json)."""
        if on and self.light_pass is None:
            from atomicworld.v3d_desktop import LightBackground
            self.light_pass = LightBackground(self.ctx)
        self.light = on
        self.engine.renderer.light = on
        self.hud.light = on
        if save:
            settings.save({"light": on})

    # ------------------------------------------------------------ cambiar de átomo
    def change_atom(self, element, isotope, keep_depth):
        """Muestra 'Construyendo…' y hace el cambio en el siguiente frame (puede tardar ~1 s)."""
        tr = self.tr
        self.hud.flash(tr.t("viewer.hud.loading", name=f"{element.symbol}-{isotope.a}"),
                       self.engine.time, 1.5)
        self.refresh_hud()

        def do():
            self.engine.isotopes_of_element = self.isotopes.of(element.number)
            self.engine.set_atom(element, isotope, keep_depth=keep_depth)
            self.hud.flash(self.engine.level.name, self.engine.time)
        self.pending = do

    def step_element(self, delta):
        number = (self.engine.element.number - 1 + delta) % len(self.table) + 1
        element = next(e for e in self.table if e.number == number)
        self.change_atom(element, self.isotopes.default(element), keep_depth=False)

    def step_isotope(self, delta):
        all_isotopes = self.isotopes.of(self.engine.element.number)
        i = next(i for i, x in enumerate(all_isotopes) if x.a == self.engine.isotope.a)
        new = all_isotopes[(i + delta) % len(all_isotopes)]
        self.change_atom(self.engine.element, new, keep_depth=True)

    # ------------------------------------------------------------ entrada (estándar común)
    # Arrastrar: lo que arrastras sigue al ratón. Botón derecho o Mayús: mover. Rueda: acercarse.
    GRAB = 1.0

    def on_mouse_press(self, x, y, button, modifiers):
        self._press = (x, y, button, modifiers, 0.0)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._press:
            px, py, b, m, moved = self._press
            self._press = (px, py, b, m, moved + abs(dx) + abs(dy))
        if buttons & (mouse.RIGHT | mouse.MIDDLE) or modifiers & key.MOD_SHIFT:
            self.engine.pan_by(dx, -dy, self.height)          # pyglet: dy > 0 = hacia arriba
        else:
            self.engine.ship.look(-dx * self.GRAB, -dy * self.GRAB)
            self.engine.autopilot = None

    def on_mouse_release(self, x, y, button, modifiers):
        press, self._press = self._press, None
        if button != mouse.LEFT or not press or press[4] > 6:
            return
        now = time.monotonic()
        t, lx, ly = self._last_click
        if now - t < 0.35 and abs(x - lx) + abs(y - ly) < 20:   # doble clic: entrar
            self._last_click = (0.0, 0, 0)
            self.do_action("go")
        else:
            self._last_click = (now, x, y)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if scroll_y:
            self.engine.zoom_by(1.15 ** scroll_y)

    def on_key_press(self, symbol, modifiers):
        action = self.keymap.action(symbol, modifiers)
        if action:
            self.do_action(action)
        if symbol == key.ESCAPE:
            return pyglet.event.EVENT_HANDLED   # Esc lo gestiona do_action, no pyglet

    def on_text(self, text):
        # los corchetes se leen como texto: así funcionan en cualquier teclado
        # (en los españoles y catalanes van con AltGr)
        action = self.keymap.text_action(text)
        if action:
            self.do_action(action)

    def do_action(self, action: str):
        tr, eng = self.tr, self.engine
        if not self.keymap.available(action):
            self.hud.flash(tr.t("viewer.hud.not_here"), eng.time, 1.5)
        elif action in ("mode", "mode_back"):
            mode = eng.toggle_mode(-1 if action == "mode_back" else 1)
            self.hud.flash(tr.t(f"viewer.hud.now_{mode}"), eng.time)
        elif action == "go":
            eng.start_autopilot("down")
        elif action == "go_full":
            eng.start_autopilot("down", full=True)
        elif action == "go_back":
            eng.start_autopilot("up")
        elif action == "reset":
            eng.reset_view()
            self.hud.flash(tr.t("viewer.hud.reset_done"), eng.time)
        elif action == "light":
            self.set_light(not self.light)
            self.hud.flash(tr.t("viewer.hud.light_on" if self.light else "viewer.hud.light_off"), eng.time)
        elif action == "more":
            self.hud.show_more = not self.hud.show_more
            self.hud.flash(tr.t("viewer.hud.more_on" if self.hud.show_more else "viewer.hud.more_off"), eng.time)
        elif action == "help":
            self.hud.show_help = not self.hud.show_help
        elif action == "fullscreen":
            self.set_fullscreen(not self.fullscreen)
        elif action == "escape":
            if eng.autopilot:
                eng.autopilot = None
                self.hud.flash(tr.t("viewer.hud.autopilot_off"), eng.time)
            else:
                self.close()
        elif action == "subshell":
            eng.cycle_subshell()
        elif action == "orbital":
            eng.cycle_orbital()
        elif action == "next_element":
            self.step_element(+1)
        elif action == "previous_element":
            self.step_element(-1)
        elif action == "next_isotope":
            self.step_isotope(+1)
        elif action == "previous_isotope":
            self.step_isotope(-1)
        self.refresh_hud()
