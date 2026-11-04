"""
Nivel 2: el núcleo atómico (unidad: femtómetro, 1 fm = 10⁻¹⁵ m).

Modos:
  - Didáctico: protones (rojo) y neutrones (gris azulado) por separado, con líneas para la
    fuerza nuclear fuerte entre vecinos (alcance ~2 fm).
  - Realista: no se puede decir "dónde" está cada nucleón (son ondas cuánticas). Se dibuja
    la densidad del núcleo entero con el perfil de Woods–Saxon. Para el hidrógeno-1 (un
    único protón) se dibuja ese protón.

La física (posiciones, perfiles) está en atomicworld/scene/nucleus.py.
"""
import numpy as np

from atomicworld import atoms
from atomicworld.constants import NEUTRON_MASS_MEV, PROTON_MASS_MEV
from viewer import scale
from viewer.levels.base import Child, Focus, Level
from viewer.render.points import LineSet, PointCloud, PointStyle
from atomicworld.scene import nucleus as nuc
from atomicworld.scene.orbitals import probability_inside_nucleus

PROTON_COLOR = (1.00, 0.36, 0.30)
NEUTRON_COLOR = (0.55, 0.68, 0.90)
REALISTIC_COLOR = (0.95, 0.82, 0.72)
REALISTIC_POINTS = 160_000
VIB_AMP_FM = 0.22          # movimiento de Fermi de los nucleones (ver time_info)
ENTER_NUCLEON_FM = 0.45    # se entra en un nucleón a 0,45 fm de su centro
EXIT_FACTOR = 4.0          # se sale al átomo a 4 × R nuclear
UNIT_PER_FM = 10.0         # el nivel del nucleón trabaja en décimas de fm


class NucleusLevel(Level):
    depth = 1
    unit_m = 1e-15

    def __init__(self, element, isotope, tr, shells):
        super().__init__(tr)
        self.el = element
        self.iso = isotope
        self.shells = shells
        self.A = isotope.a
        self.R = atoms.nuclear_radius_fm(self.A)
        rng = np.random.default_rng(element.number * 1000 + isotope.a)
        self.centers = nuc.pack_nucleons(self.A, self.R, rng)
        self.kinds = nuc.assign_kinds(element.protons, isotope.neutrons, rng)
        self.clouds = []
        self.lines = []

    @property
    def name(self):
        tr = self.tr
        return tr.t("viewer.levels.nucleus", element=tr.element(self.el.number),
                    of_element=tr.of(tr.element(self.el.number)), a=self.A)

    # ------------------------------------------------------------ construcción
    def build(self, renderer, didactic):
        rng = np.random.default_rng(7)
        if didactic or self.A == 1:
            ppn = nuc.points_per_nucleon(self.A)
            pos, owner = nuc.nucleon_clouds(self.centers, ppn, rng)
            if didactic:
                rgb = np.where((self.kinds[owner] == "p")[:, None], PROTON_COLOR, NEUTRON_COLOR)
            else:
                rgb = np.tile(REALISTIC_COLOR, (len(pos), 1))
            alpha = 0.22 if self.A < 60 else 0.16
            col = np.hstack([rgb, np.full((len(pos), 1), alpha)])
            # misma semilla en todo el nucleón: vibra como un bloque
            self.clouds.append(("nucleons", PointCloud(renderer, pos, col, np.full(len(pos), 0.03),
                                                       owner.astype("f4"))))
        else:
            n = REALISTIC_POINTS
            r = nuc.sample_woods_saxon(n, self.R, nuc.WS_DIFFUSENESS_FM, rng)
            pts = nuc.directions(n, rng) * r[:, None]
            col = np.tile([*REALISTIC_COLOR, 0.18], (n, 1))
            self.clouds.append(("matter", PointCloud(renderer, pts, col, np.full(n, 0.03),
                                                     rng.random(n).astype("f4") * 1000)))
        if didactic and self.A > 1:
            a, b = nuc.strong_bonds(self.centers)
            c = np.tile([0.45, 1.0, 0.55, 0.75 if self.A < 60 else 0.3], (len(a), 1))
            self.lines.append(LineSet(renderer, a, b, c))

    def release(self):
        for _, c in self.clouds:
            c.release()
        for line in self.lines:
            line.release()
        self.clouds, self.lines = [], []

    # ------------------------------------------------------------ dibujo
    def render(self, renderer, cam, didactic, fade):
        for kind, cloud in self.clouds:
            if kind == "nucleons":
                style = PointStyle(vib_amp=VIB_AMP_FM, min_px=1.5, max_px=5, softness=0.8)
            else:
                style = PointStyle(twinkle=0.4, min_px=1.5, max_px=5, softness=0.8)
            renderer.points(cloud, cam, style, fade)
        for line in self.lines:
            renderer.lines(line, cam, fade, 0.12)

    # ------------------------------------------------------------ navegación
    def surface_distance(self, pos):
        d = np.linalg.norm(self.centers - pos, axis=1).min()
        return float(max(d * 0.6, 0.05))

    def view_distance(self):
        return max(2.6 * self.R, 4.0)

    def _nucleon_ahead(self, pos, forward, cone_deg=6.0):
        v = self.centers - pos
        d = np.linalg.norm(v, axis=1)
        cos = (v @ forward) / np.maximum(d, 1e-9)
        score = np.where((cos > np.cos(np.radians(cone_deg))) | (d < nuc.NUCLEON_RMS_FM), d, np.inf)
        k = int(np.argmin(score))
        return (k, d[k]) if np.isfinite(score[k]) else (None, None)

    def child_to_enter(self, pos):
        d = np.linalg.norm(self.centers - pos, axis=1)
        k = int(np.argmin(d))
        if d[k] >= ENTER_NUCLEON_FM:
            return None
        from viewer.levels.nucleon import NucleonLevel
        others = [j for j in range(self.A) if j != k]
        rel = (self.centers[others] - self.centers[k]) * UNIT_PER_FM
        kinds = [str(self.kinds[j]) for j in others]
        kind = str(self.kinds[k])
        return Child(key=("nucleon", self.el.number, self.A, k), center=self.centers[k].copy(),
                     scale=UNIT_PER_FM,
                     create=lambda: NucleonLevel(kind, k, self.tr, neighbors=rel, neighbor_kinds=kinds))

    def dive_target(self, pos, forward):
        k, _ = self._nucleon_ahead(pos, forward, cone_deg=25)
        if k is None:      # ninguno delante: el más cercano a la nave
            k = int(np.argmin(np.linalg.norm(self.centers - pos, axis=1)))
        return self.centers[k], self.tr.t("viewer.hud.target_nucleon")

    def should_exit(self, pos):
        return np.linalg.norm(pos) > EXIT_FACTOR * self.R

    def focus(self, pos, forward, didactic):
        tr = self.tr
        k, dist = self._nucleon_ahead(pos, forward)
        realistic_blob = not didactic and self.A > 1
        if k is not None and not realistic_blob:
            kind = "proton" if self.kinds[k] == "p" else "neutron"
            mass = PROTON_MASS_MEV if kind == "proton" else NEUTRON_MASS_MEV
            expl = []
            if didactic:
                expl = tr.lines(f"viewer.nucleus.{kind}.explanation")
                if self.A > 1:
                    expl.append(tr.t("viewer.nucleus.strong_lines"))
            detail = tr.t(f"viewer.nucleus.{kind}.detail", mass=tr.num(mass, 2))
            return Focus(tr.t(f"viewer.nucleus.{kind}.title"),
                         detail + " · " + tr.t("viewer.nucleus.go_in"), expl, distance=dist)

        p_in = probability_inside_nucleus(self.el.protons, self.shells, self.R / 1000)
        protons = tr.count(self.el.protons, "proton")
        expl = []
        if didactic:
            key = "explanation_hydrogen" if self.el.protons == 1 else "explanation"
            expl = tr.lines(f"viewer.nucleus.{key}", protons=protons, p_in=tr.sci(p_in))
        elif self.A > 1:
            expl = tr.lines("viewer.nucleus.explanation_realistic")
        if self.iso.status == "radioactive" and self.iso.decay:
            expl.append(tr.t("viewer.nucleus.unstable", decay=scale.decay_text(self.iso, tr)))
        title = tr.t("viewer.nucleus.title", protons=protons,
                     neutrons=tr.count(self.iso.neutrons, "neutron"), r=tr.num(self.R, 1))
        detail = tr.t("viewer.nucleus.detail", rho=tr.sci(nuc.density_kg_m3(self.A, self.R)))
        return Focus(title, detail, expl, distance=float(np.linalg.norm(pos)))

    def time_info(self):
        return self.tr.t("viewer.nucleus.time")
