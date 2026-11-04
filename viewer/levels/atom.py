"""
Nivel 1: el átomo aislado (unidad: picómetro, 1 pm = 10⁻¹² m).

Se ve:
  - La nube de electrones, muestreada de |ψ|² (atomicworld/scene/orbitals.py).
  - El núcleo, a su tamaño real: unas 50.000 veces más pequeño que el átomo. Desde fuera
    es invisible; hay que cruzar un "vacío" enorme hasta verlo aparecer. En modo didáctico
    lleva un marcador de 5 píxeles para saber hacia dónde ir.
"""
import numpy as np

from atomicworld import atoms
from viewer.levels.base import Child, Focus, Level
from viewer.render.points import LineSet, PointCloud, PointStyle
from atomicworld.scene import orbitals

SHELL_COLORS = {1: (1.00, 0.72, 0.30), 2: (0.30, 0.85, 1.00), 3: (0.78, 0.50, 1.00),
                4: (0.40, 1.00, 0.55), 5: (1.00, 0.45, 0.70), 6: (1.00, 0.95, 0.40),
                7: (0.50, 0.60, 1.00)}
REALISTIC_COLOR = np.array([0.55, 0.70, 1.00])
NUCLEUS_COLOR = (1.0, 0.45, 0.35, 1.0)
# un color por orbital en la vista de un subnivel (tecla O): se distingue qué lóbulo es de cuál
ORBITAL_COLORS = [(1.00, 0.55, 0.25), (0.30, 0.85, 1.00), (0.55, 1.00, 0.40), (1.00, 0.40, 0.75),
                  (1.00, 0.92, 0.35), (0.65, 0.55, 1.00), (0.35, 1.00, 0.85)]
DETAIL_POINTS = 150_000     # puntos de lo que se muestra con O / I, tenga 1 electrón o 14
AXIS_COLORS = {"x": (1.0, 0.45, 0.45), "y": (0.45, 1.0, 0.45), "z": (0.45, 0.65, 1.0)}
ENTRY_FACTOR = 3.0          # se entra en el núcleo a 3 × su radio
MAX_DISTANCE_FACTOR = 40    # la nave no se aleja más de 40 radios atómicos


class AtomLevel(Level):
    depth = 0
    unit_m = 1e-12

    def __init__(self, element, isotope, tr):
        super().__init__(tr)
        self.el = element
        self.iso = isotope
        self.shells = atoms.subshells(element)
        self.vdw_pm = element.vdw_radius_pm
        self.nucleus_r_pm = atoms.nuclear_radius_fm(isotope.a) / 1000
        self.clouds = {}
        self.view = None            # None: todos los electrones; i: solo el subnivel self.shells[i]
        self.orbital = None         # con un subnivel elegido: None = todos sus orbitales; k = solo uno
        self.renderer = None
        self.didactic = True

    @property
    def name(self):
        tr = self.tr
        return tr.t("viewer.levels.atom", element=tr.element(self.el.number),
                    of_element=tr.of(tr.element(self.el.number)), a=self.iso.a)

    # ------------------------------------------------------------ construcción
    def build(self, renderer, didactic):
        rng = np.random.default_rng(self.el.number)
        if didactic:
            ppe = orbitals.didactic_points(self.el.protons, self.shells)
        else:
            ppe = orbitals.points_per_electron(self.el.electrons)
        pts, shells_n, shells_l = orbitals.sample_atom(self.el.protons, self.shells, ppe, didactic, rng)
        if didactic:
            palette = np.array([SHELL_COLORS[n] for n in sorted(SHELL_COLORS)])
            col = palette[shells_n - 1]
            alpha, size = self._didactic_style(shells_n, shells_l)
        else:
            col = np.tile(REALISTIC_COLOR, (len(pts), 1))
            # con muchos electrones hay muchos más puntos juntos: se baja un poco el brillo
            alpha = np.full(len(pts), 0.30 if self.el.electrons <= 10 else 0.22)
            size = np.full(len(pts), 0.9)
        col = np.hstack([col, alpha[:, None]])
        seed = rng.random(len(pts)).astype("f4") * 1000
        self.clouds["electrons"] = PointCloud(renderer, pts, col, size, seed)
        self.renderer, self.didactic = renderer, didactic
        if not didactic:
            self.orbital = None             # en modo realista no hay orbitales sueltos
        self._build_detail()
        self.clouds["nucleus"] = PointCloud(renderer, np.zeros((1, 3)), np.array([NUCLEUS_COLOR]),
                                            np.array([self.nucleus_r_pm]), np.zeros(1))

    def _didactic_style(self, shells_n, shells_l):
        """Brillo y tamaño de cada punto según su subnivel (ver orbitals.didactic_style)."""
        alpha = np.empty(len(shells_n), dtype="f4")
        size = np.empty(len(shells_n), dtype="f4")
        for (n, l), (a, sz) in orbitals.didactic_style(self.el.protons, self.shells).items():
            mask = (shells_n == n) & (shells_l == l)
            alpha[mask], size[mask] = a, sz
        return alpha, size

    # ------------------------------------------------------------ un subnivel cada vez (teclas O e I)
    def cycle_view(self):
        """Tecla O. Todos → el subnivel más externo → ... → el 1s → todos otra vez."""
        order = [None] + list(range(len(self.shells) - 1, -1, -1))
        self.view = order[(order.index(self.view) + 1) % len(order)]
        self.orbital = None
        self._build_detail()
        return self.view

    def cycle_orbital(self):
        """Tecla I, con un subnivel p, d o f elegido: sus orbitales ocupados de uno en uno."""
        if self.view is None or self.shells[self.view].l == 0 or not self.didactic:
            return False
        sh = self.shells[self.view]
        occupied = [k for k, e in enumerate(orbitals.hund_occupancy(sh.l, sh.electrons)) if e]
        order = [None] + occupied
        self.orbital = order[(order.index(self.orbital) + 1) % len(order)]
        self._build_detail()
        return True

    def subshell_label(self, i) -> str:
        return _superscript(self.shells[i].label)

    def orbital_label(self) -> str:
        sh = self.shells[self.view]
        return f"{sh.n}{orbitals.orbital_names(sh.l)[self.orbital]}"

    def frame_distance(self) -> float:
        """Distancia a la que se ve entero lo que se está mostrando (tecla O)."""
        if self.view is None:
            return self.view_distance()
        sh = self.shells[self.view]
        zeff = atoms.slater_zeff(self.el.protons, self.shells, sh.n, sh.l)
        return 3.4 * orbitals.mean_radius_pm(sh.n, sh.l, zeff)

    def _build_detail(self):
        """La nube del subnivel elegido, generada aparte y con muchos puntos: en la vista de
        todos los electrones los internos llevan pocos, y solos casi no se verían."""
        for key in ("detail", "axes"):
            old = self.clouds.pop(key, None)
            if old:
                old.release()
        if self.view is None or self.renderer is None:
            return
        rng = np.random.default_rng(1000 + self.view)
        sh = self.shells[self.view]
        shown = sh.electrons if self.orbital is None else \
            orbitals.hund_occupancy(sh.l, sh.electrons)[self.orbital]
        pts, owner = orbitals.sample_subshell(self.el.protons, self.shells, self.view,
                                              DETAIL_POINTS // shown, self.didactic, rng,
                                              only=self.orbital)
        if self.didactic:
            rgb = np.array(ORBITAL_COLORS)[owner % len(ORBITAL_COLORS)]
            if self.shells[self.view].l == 0:
                rgb = np.tile(SHELL_COLORS[self.shells[self.view].n], (len(pts), 1))
        else:
            rgb = np.tile(REALISTIC_COLOR, (len(pts), 1))
        col = np.hstack([rgb, np.full((len(pts), 1), 0.4)])
        self.clouds["detail"] = PointCloud(self.renderer, pts, col, np.full(len(pts), 0.9),
                                           rng.random(len(pts)).astype("f4") * 1000)
        if self.didactic:          # ejes x, y, z: los nombres de los orbitales (dxy, dz²...) se refieren a ellos
            half = self.axis_length()
            a = np.array([[-half, 0, 0], [0, -half, 0], [0, 0, -half]])
            colors = np.array([[*AXIS_COLORS[k], 0.55] for k in "xyz"])
            self.clouds["axes"] = LineSet(self.renderer, a, -a, colors)

    def axis_length(self) -> float:
        sh = self.shells[self.view]
        return 2.0 * orbitals.mean_radius_pm(sh.n, sh.l, atoms.slater_zeff(self.el.protons, self.shells, sh.n, sh.l))

    def axis_labels(self):
        """Puntas de los ejes (para escribir x, y, z en el HUD), o [] si no se muestran."""
        if "axes" not in self.clouds:
            return []
        half = self.axis_length() * 1.05
        return [(np.array(v, dtype=float) * half, k) for k, v in
                (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1)))]

    def release(self):
        for c in self.clouds.values():
            c.release()
        self.clouds = {}

    # ------------------------------------------------------------ dibujo
    def render(self, renderer, cam, didactic, fade):
        cloud = self.clouds["detail"] if self.view is not None else self.clouds["electrons"]
        renderer.points(cloud, cam, PointStyle(twinkle=0.5, min_px=1.5, max_px=7, softness=0.85), fade)
        if "axes" in self.clouds:
            renderer.lines(self.clouds["axes"], cam, fade * 0.8, 0.0)
        # El núcleo: en modo realista, tamaño real (invisible hasta acercarse mucho).
        # En modo didáctico, un marcador mínimo de 5 px para saber dónde está.
        renderer.points(self.clouds["nucleus"], cam,
                        PointStyle(min_px=5.0 if didactic else 0.5, max_px=900, softness=0.6), fade)

    # ------------------------------------------------------------ navegación
    def surface_distance(self, pos):
        return float(max(np.linalg.norm(pos) - self.nucleus_r_pm, self.nucleus_r_pm * 0.5))

    def max_distance(self):
        return MAX_DISTANCE_FACTOR * self.vdw_pm

    def view_distance(self):
        """Lo bastante lejos para ver la capa más externa entera."""
        return orbitals.atom_view_distance(self.vdw_pm, self.el.protons, self.shells)

    def child_to_enter(self, pos):
        from viewer.levels.nucleus import NucleusLevel
        if np.linalg.norm(pos) < ENTRY_FACTOR * self.nucleus_r_pm:
            return Child(key=("nucleus", self.el.number, self.iso.a), center=np.zeros(3),
                         scale=1000.0,
                         create=lambda: NucleusLevel(self.el, self.iso, self.tr, self.shells))
        return None

    def dive_target(self, pos, forward):
        return np.zeros(3), self.tr.t("viewer.hud.target_nucleus")

    def focus(self, pos, forward, didactic):
        tr, el = self.tr, self.el
        r = np.linalg.norm(pos)
        to_nuc = -pos / max(r, 1e-12)
        if self.view is not None and r > 5:       # con un subnivel elegido (tecla O), manda él
            return self._subshell_focus(didactic, r)
        if forward @ to_nuc > np.cos(np.radians(4)) or r < 5:
            title = tr.t("viewer.atom.nucleus_title", element=tr.element(el.number),
                         of_element=tr.of(tr.element(el.number)),
                         protons=tr.count(el.protons, "proton"),
                         neutrons=tr.count(self.iso.neutrons, "neutron"))
            expl = []
            if didactic:
                ratio = self.vdw_pm / self.nucleus_r_pm
                expl = tr.lines("viewer.atom.nucleus_explanation",
                                r=tr.num(self.nucleus_r_pm * 1000, 1), ratio=tr.int(round(ratio, -3)))
            return Focus(title, tr.t("viewer.atom.nucleus_distance", d=tr.num(r, 2)), expl, distance=r)

        config = " ".join(_superscript(s.label) for s in self.shells)
        expl = []
        if didactic:
            zeff = ", ".join(f"{s.name} {tr.num(atoms.slater_zeff(el.protons, self.shells, s.n, s.l), 2)}"
                             for s in self.shells[-4:])
            expl = [tr.t("viewer.atom.zeff", zeff=zeff)] + tr.lines("viewer.atom.cloud_explanation")
        else:
            expl = tr.lines("viewer.atom.cloud_explanation_realistic")
        return Focus(tr.t("viewer.atom.cloud_title", electrons=tr.count(el.electrons, "electron")),
                     tr.t("viewer.atom.cloud_detail", config=config), expl, distance=r)

    def _subshell_focus(self, didactic, r):
        tr, sh = self.tr, self.shells[self.view]
        zeff = atoms.slater_zeff(self.el.protons, self.shells, sh.n, sh.l)
        letter = "spdf"[sh.l]
        if sh.l == 0:
            boxes = "s " + _boxes(sh.electrons)
        else:
            names = orbitals.orbital_names(sh.l)
            occ = orbitals.hund_occupancy(sh.l, sh.electrons)
            boxes = " · ".join((f"[{n} {_boxes(e)}]" if k == self.orbital else f"{n} {_boxes(e)}")
                               for k, (n, e) in enumerate(zip(names, occ)))
        expl = [tr.t("viewer.atom.subshell_zeff", zeff=tr.num(zeff, 2),
                     r=tr.num(orbitals.mean_radius_pm(sh.n, sh.l, zeff), 0))]
        if didactic:
            expl.append(tr.t(f"viewer.atom.shape.{letter}", nodes=sh.n - sh.l - 1))
            if sh.l > 0:
                expl.append(tr.t("viewer.atom.hund"))
                expl.append(tr.t("viewer.atom.full" if sh.is_full else "viewer.atom.partial"))
                expl.append(tr.t("viewer.atom.orbital_colors"))
        else:
            expl.append(tr.t("viewer.atom.realistic_subshell"))
        if self.orbital is not None:
            e = orbitals.hund_occupancy(sh.l, sh.electrons)[self.orbital]
            title = tr.t("viewer.atom.orbital_title", name=self.orbital_label(),
                         electrons=tr.count(e, "electron"))
        else:
            title = tr.t("viewer.atom.subshell_title", name=self.subshell_label(self.view),
                         electrons=tr.count(sh.electrons, "electron"))
        return Focus(title, boxes, expl, distance=r)

    def time_info(self):
        return self.tr.t("viewer.atom.time")


_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _boxes(electrons: int) -> str:
    """Casilla de un orbital: '↑↓', '↑' o '—' (vacío)."""
    return {2: "↑↓", 1: "↑"}.get(electrons, "—")


def _superscript(label: str) -> str:
    """'3d10' -> '3d¹⁰'"""
    return label[:2] + label[2:].translate(_SUP)
