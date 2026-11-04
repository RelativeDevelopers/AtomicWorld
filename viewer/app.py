"""
La ventana del visor: controles, bucle y teclas.

    python -m viewer Fe                       (hierro, isótopo más abundante)
    python -m viewer Uranio --isotope 235     (cualquier idioma, símbolo o número atómico)
    python -m viewer 6 --isotope 14 --lang ca --realistic
"""
import moderngl
import numpy as np
import pyglet
from pyglet.window import key, mouse

from atomicworld.repository import IsotopeTable, PeriodicTable
from ui import settings
from viewer.engine import Engine
from viewer.hud import HUD


class App(pyglet.window.Window):
    def __init__(self, element, isotope, tr, didactic=True, table=None, isotopes=None):
        self.tr = tr
        self.table = table or PeriodicTable()
        self.isotopes = isotopes or IsotopeTable()
        config = pyglet.gl.Config(double_buffer=True, major_version=3, minor_version=3,
                                  forward_compatible=True, sample_buffers=1, samples=4)
        try:
            super().__init__(1600, 900, tr.t("viewer.title"), resizable=True, config=config)
        except pyglet.window.NoSuchConfigException:
            super().__init__(1600, 900, tr.t("viewer.title"), resizable=True)
        self.ctx = moderngl.create_context()
        print("GPU:", self.ctx.info["GL_RENDERER"])
        if "Intel" in self.ctx.info["GL_RENDERER"]:
            print("WARNING: using the integrated graphics card. On Windows, choose the NVIDIA one in "
                  "Settings > System > Display > Graphics.")

        self.engine = Engine(self.ctx, element, isotope, tr, didactic, self.isotopes.of(element.number))
        self.hud = HUD(self.ctx, tr)
        self.hud_timer = 0.0
        self.pending = None               # cambio de átomo que se hace en el siguiente frame
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.captured = False
        self.hud.flash(tr.t("viewer.hud.click"), 0.0, 4.0)
        pyglet.clock.schedule_interval(self.tick, 1 / 144)

    # ------------------------------------------------------------ bucle
    def tick(self, dt):
        if self.pending:                   # se ejecuta después de haber dibujado el aviso
            action, self.pending = self.pending, None
            action()
            dt = 1 / 60
        dt = min(dt, 0.05)
        k = self.keys
        move = np.array([
            (k[key.D] - k[key.A]),
            (k[key.SPACE] - (k[key.LCTRL] or k[key.RCTRL])),
            (k[key.W] - k[key.S]),
        ], dtype=float)
        if k[key.Q]:
            self.engine.ship.roll(1.2 * dt)
        if k[key.E]:
            self.engine.ship.roll(-1.2 * dt)
        prev_level = self.engine.level
        self.engine.update(dt, move, k[key.LSHIFT] or k[key.RSHIFT])
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
        self.hud.upload(self.hud.compose(self.engine.hud_state(w, h), w, h, self.engine.time))

    def on_draw(self):
        w, h = self.get_framebuffer_size()
        self.ctx.screen.use()
        self.engine.render(w, h)
        self.hud.draw()

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

    # ------------------------------------------------------------ entrada
    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT and not self.captured:
            self.captured = True
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.captured:
            self.engine.ship.look(dx, dy)
            self.engine.autopilot = None

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.engine.ship.look(dx, dy)
        self.engine.autopilot = None

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        s = self.engine.ship
        s.speed_mult = float(np.clip(s.speed_mult * (1.25 ** scroll_y), 0.05, 20))

    def on_key_press(self, symbol, modifiers):
        tr, eng = self.tr, self.engine
        if symbol == key.ESCAPE:
            if self.captured:
                self.captured = False
                self.set_exclusive_mouse(False)
            else:
                self.close()
            return pyglet.event.EVENT_HANDLED   # que Esc no cierre la ventana directamente
        if symbol == key.TAB:
            eng.toggle_mode()
            self.hud.flash(tr.t("viewer.hud.now_didactic" if eng.didactic else "viewer.hud.now_realistic"),
                           eng.time)
        elif symbol in (key.ENTER, key.RETURN, key.NUM_ENTER):
            eng.start_autopilot("down")
        elif symbol == key.BACKSPACE:
            eng.start_autopilot("up")
        elif symbol == key.O:
            eng.cycle_subshell()
        elif symbol == key.I:
            eng.cycle_orbital()
        elif symbol == key.N:
            self.step_element(+1)
        elif symbol == key.P:
            self.step_element(-1)
        elif symbol == key.L:
            settings.save({"language": tr.next_language()})
            self.set_caption(tr.t("viewer.title"))
            self.hud.flash(tr.t("viewer.hud.language"), eng.time)
        elif symbol == key.H:
            self.hud.show_help = not self.hud.show_help
        elif symbol == key.F11:
            self.set_fullscreen(not self.fullscreen)
        self.refresh_hud()

    def on_text(self, text):
        # los corchetes se leen como texto: así funcionan en cualquier teclado
        # (en los españoles y catalanes van con AltGr)
        if text == "]":
            self.step_isotope(+1)
        elif text == "[":
            self.step_isotope(-1)
