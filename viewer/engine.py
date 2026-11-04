"""
Motor: pila de niveles, transiciones con fundido, autopiloto y dibujo.

    pila = [AtomLevel, NucleusLevel, NucleonLevel]   (el último es donde está la nave)

La nave siempre vive en las coordenadas del nivel superior de la pila. Al entrar en un
hijo se apila; al salir se desapila. Durante ~0,6 s se dibujan ambos niveles con un
fundido cruzado.
"""
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from viewer.levels.atom import AtomLevel
from viewer.levels.base import Level
from viewer.mathutil import perspective, view_matrix
from viewer.render.points import Camera, Renderer
from viewer.ship import Ship

FOV_Y = 70.0
TRANSITION_TIME = 0.6
CACHE_SIZE = 4
START_DIRECTION = np.array([1.0, -0.35, 0.25]) / np.linalg.norm([1.0, -0.35, 0.25])
TURN_RATE = 5.0            # rapidez con la que el autopiloto gira la nave hacia el destino
AUTOPILOT_CRUISE = (2.5, 1.5, 1.0)   # velocidad del autopiloto al bajar, por nivel (× normal)


@dataclass
class Transition:
    old: Level
    to_old: Callable[[np.ndarray], np.ndarray]   # posición actual -> coords del nivel viejo
    t: float = 0.0


@dataclass
class Autopilot:
    mode: str                    # "down" (bajar un nivel), "up" (subir) o "frame" (encuadrar)
    start_depth: int
    distance: float = 0.0        # para "frame": a qué distancia del centro colocarse
    target: Optional[Callable[[], np.ndarray]] = None
    target_depth: int = -1


class Engine:
    def __init__(self, ctx, element, isotope, tr, didactic=True, isotopes_of_element=()):
        self.renderer = Renderer(ctx)
        self.isotopes_of_element = list(isotopes_of_element)   # para "isótopo i de N" en el HUD
        self.tr = tr
        self.didactic = didactic
        self.time = 0.0
        self.stack = []
        self.cache: OrderedDict = OrderedDict()
        self.transition: Optional[Transition] = None
        self.autopilot: Optional[Autopilot] = None
        self.messages: list[str] = []                # avisos para el HUD (el motor no dibuja texto)
        self.set_atom(element, isotope)

    # ------------------------------------------------------------ átomo actual
    def set_atom(self, element, isotope, keep_depth=False):
        """Cambia de elemento o de isótopo. Con keep_depth, si estabas en el núcleo o dentro
        de un nucleón, apareces en el núcleo nuevo (útil para comparar isótopos)."""
        go_to_nucleus = keep_depth and self.stack and self.level.depth >= 1
        self._release_all()
        self.element, self.isotope = element, isotope
        root = AtomLevel(element, isotope, self.tr)
        root.build(self.renderer, self.didactic)
        self.stack = [(root, None)]
        self.transition = None
        self.autopilot = None
        start = START_DIRECTION * root.view_distance()
        self.ship = Ship(start, look_at=np.zeros(3))
        if go_to_nucleus:
            child = root.child_to_enter(np.zeros(3))
            new = self._get_level(child)
            self.stack.append((new, child))
            self.ship = Ship(START_DIRECTION * new.view_distance(), look_at=np.zeros(3))

    def _release_all(self):
        for lvl, _ in self.stack:
            lvl.release()
        for lvl in self.cache.values():
            if not any(lvl is s for s, _ in self.stack):
                lvl.release()
        self.cache.clear()
        self.stack = []

    # ------------------------------------------------------------ propiedades
    @property
    def level(self) -> Level:
        return self.stack[-1][0]

    @property
    def root(self) -> Level:
        return self.stack[0][0]

    def surface_distance(self) -> float:
        return self.level.surface_distance(self.ship.pos)

    # ------------------------------------------------------------ lógica
    def update(self, dt, move, boost):
        self.time += dt
        if np.any(move) and self.autopilot:          # tocar los controles cancela el autopiloto
            self.autopilot = None
        if self.autopilot:
            move, boost = self._autopilot_step(dt)
        self.level.update(dt, self.time)
        if self.transition:
            self.transition.old.update(dt, self.time)
        self.ship.update(dt, move, boost, self.surface_distance())
        if len(self.stack) == 1:                     # no perderse en el vacío
            r = np.linalg.norm(self.ship.pos)
            limit = self.root.max_distance()
            if r > limit:
                self.ship.pos *= limit / r
        self._check_level_change()
        if self.transition:
            self.transition.t += dt / TRANSITION_TIME
            if self.transition.t >= 1:
                self.transition = None

    def _check_level_change(self):
        level = self.level
        if len(self.stack) > 1 and level.should_exit(self.ship.pos):
            child = self.stack[-1][1]
            self.stack.pop()
            self.ship.unscale(child.center, child.scale)
            self.transition = Transition(level, lambda p, c=child: (p - c.center) * c.scale)
            return
        child = level.child_to_enter(self.ship.pos)
        if child is not None:
            new = self._get_level(child)
            self.ship.rescale(child.center, child.scale)
            self.stack.append((new, child))
            self.transition = Transition(level, lambda p, c=child: p / c.scale + c.center)

    def _get_level(self, child) -> Level:
        if child.key in self.cache:
            self.cache.move_to_end(child.key)
            return self.cache[child.key]
        lvl = child.create()
        lvl.build(self.renderer, self.didactic)
        self.cache[child.key] = lvl
        while len(self.cache) > CACHE_SIZE:
            key, old = next(iter(self.cache.items()))
            if any(old is s for s, _ in self.stack):
                self.cache.move_to_end(key)
                break
            self.cache.popitem(last=False)
            old.release()
        return lvl

    def toggle_mode(self):
        self.didactic = not self.didactic
        levels = [s for s, _ in self.stack] + [c for c in self.cache.values()
                                                 if not any(c is s for s, _ in self.stack)]
        for lvl in levels:
            lvl.set_mode(self.renderer, self.didactic)
        self.transition = None

    def cycle_subshell(self):
        """Tecla O: en el átomo, mostrar los subniveles de uno en uno."""
        root = self.root
        view = root.cycle_view()
        if view is None:
            self.messages.append(self.tr.t("viewer.hud.showing_all"))
        else:
            self.messages.append(self.tr.t("viewer.hud.showing_subshell", name=root.subshell_label(view)))
        if len(self.stack) == 1:                     # en el átomo: encuadrar lo que se ve
            self.autopilot = Autopilot("frame", 0, distance=root.frame_distance())

    def cycle_orbital(self):
        """Tecla I: con un subnivel p, d o f elegido, sus orbitales de uno en uno."""
        root = self.root
        if not root.cycle_orbital():
            return
        if root.orbital is None:
            self.messages.append(self.tr.t("viewer.hud.showing_subshell", name=root.subshell_label(root.view)))
        else:
            self.messages.append(self.tr.t("viewer.hud.showing_orbital", name=root.orbital_label()))

    # ------------------------------------------------------------ autopiloto
    def start_autopilot(self, mode: str):
        """Enter: bajar al siguiente nivel. Retroceso: volver al anterior."""
        tr = self.tr
        if mode == "up" and len(self.stack) == 1 and \
                np.linalg.norm(self.ship.pos) >= self.root.view_distance() * 0.95:
            self.messages.append(tr.t("viewer.hud.already_outside"))
            return
        self.autopilot = Autopilot(mode, self.level.depth)
        if mode == "down":
            self._aim_dive()
            self.messages.append(tr.t("viewer.hud.autopilot_down", target=self._dive_label))
        else:
            self.messages.append(tr.t("viewer.hud.autopilot_up"))

    def _aim_dive(self):
        level, ap = self.level, self.autopilot
        point, self._dive_label = level.dive_target(self.ship.pos, self.ship.forward)
        if hasattr(level, "nearest_quark"):          # dentro del nucleón: seguir al quark que se mueve
            k, _ = level.nearest_quark(self.ship.pos)
            ap.target = lambda lv=level, k=k: lv.quark_pos[k]
        else:
            fixed = np.array(point, dtype=float)
            ap.target = lambda p=fixed: p
        ap.target_depth = level.depth

    def _turn_towards(self, direction, dt):
        s = self.ship
        k = 1 - np.exp(-dt * TURN_RATE)
        f = s.forward + (direction - s.forward) * k
        f /= np.linalg.norm(f)
        up = s.up if abs(f @ s.up) < 0.99 else s.right
        right = np.cross(f, up)
        right /= np.linalg.norm(right)
        s.orient = np.column_stack([right, np.cross(right, f), -f])

    def _arrive(self):
        """Fin del autopiloto: frenar en seco (si no, la inercia atraviesa el núcleo)."""
        self.autopilot = None
        self.ship.vel[:] = 0.0
        return np.zeros(3), False

    def _autopilot_step(self, dt):
        ap, level, pos = self.autopilot, self.level, self.ship.pos
        if ap.mode == "down":
            if level.depth > ap.start_depth:         # ya hemos entrado
                return self._arrive()
            if level.depth != ap.target_depth:       # se salió por el camino: nuevo destino
                self._aim_dive()
            target = ap.target()
            v = target - pos
            dist = np.linalg.norm(v)
            if hasattr(level, "nearest_quark"):
                from viewer.levels.nucleon import QUARK_STOP
                if dist < QUARK_STOP:
                    self.messages.append(self.tr.t("viewer.hud.end_of_journey"))
                    return self._arrive()
            self._turn_towards(v / max(dist, 1e-12), dt)
            aligned = self.ship.forward @ (v / max(dist, 1e-12))
            # el viaje del átomo al núcleo es de ~5 órdenes de magnitud: algo más deprisa
            cruise = AUTOPILOT_CRUISE[min(level.depth, len(AUTOPILOT_CRUISE) - 1)]
            return np.array([0.0, 0.0, cruise if aligned > 0.7 else 0.2]), False
        if ap.mode == "frame":
            r = np.linalg.norm(pos)
            if len(self.stack) > 1 or abs(r - ap.distance) < 0.04 * ap.distance:
                return self._arrive()
            self._turn_towards(-pos / max(r, 1e-12), dt)
            # hacia delante si estás lejos, hacia atrás si estás cerca; más suave al llegar
            return np.array([0.0, 0.0, float(np.clip(4 * (r - ap.distance) / r, -1.5, 1.5))]), False
        # subir: mirar al centro del nivel y retroceder
        r = np.linalg.norm(pos)
        if level.depth < ap.start_depth or len(self.stack) == 1:
            if r >= level.view_distance():
                return self._arrive()
        self._turn_towards(-pos / max(r, 1e-12), dt)
        return np.array([0.0, 0.0, -1.0]), True

    # ------------------------------------------------------------ dibujo
    def _camera(self, level, pos, width, height) -> Camera:
        d = max(level.surface_distance(pos), 1e-12)
        near = d * 0.02
        far = near * 1e7
        proj = perspective(FOV_Y, width / max(height, 1), near, far)
        return Camera(view_matrix(pos, self.ship.orient), proj, height, self.time)

    def render(self, width, height):
        r = self.renderer
        r.ctx.viewport = (0, 0, width, height)
        r.begin()
        fade_new = 1.0
        if self.transition:
            tr = self.transition
            s = min(tr.t, 1.0)
            fade_new = s * s * (3 - 2 * s)     # suavizado
            old_pos = tr.to_old(self.ship.pos)
            tr.old.render(r, self._camera(tr.old, old_pos, width, height),
                          self.didactic, 1.0 - fade_new)
        self.level.render(r, self._camera(self.level, self.ship.pos, width, height),
                          self.didactic, fade_new)

    # ------------------------------------------------------------ datos para el HUD
    def project(self, point, width, height):
        """Punto del nivel actual -> píxel de la pantalla (None si queda detrás de la cámara)."""
        cam = self._camera(self.level, self.ship.pos, width, height)
        clip = cam.proj @ cam.view @ np.append(point, 1.0)
        if clip[3] <= 0:
            return None
        ndc = clip[:3] / clip[3]
        return (ndc[0] + 1) / 2 * width, (1 - ndc[1]) / 2 * height

    def hud_state(self, width, height) -> dict:
        lvl = self.level
        labels = []
        if len(self.stack) == 1 and not self.transition:
            for point, name in self.root.axis_labels():
                px = self.project(point, width, height)
                if px:
                    labels.append((px, name))
        d = self.surface_distance()
        aspect = width / max(height, 1)
        visible_w = 2 * d * np.tan(np.radians(FOV_Y) / 2) * aspect * lvl.unit_m
        return {
            "level": lvl,
            "depth_m": d * lvl.unit_m,
            "visible_width_m": visible_w,
            "speed_m_s": np.linalg.norm(self.ship.vel) * lvl.unit_m,
            "focus": lvl.focus(self.ship.pos, self.ship.forward, self.didactic),
            "time": lvl.time_info(),
            "didactic": self.didactic,
            "speed_mult": self.ship.speed_mult,
            "element": self.element,
            "isotope": self.isotope,
            "autopilot": self.autopilot is not None,
            "isotopes": self.isotopes_of_element,
            "axis_labels": labels,
        }
