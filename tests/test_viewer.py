"""Tests del visor 3D y de los textos del escritorio.

La física y los textos se prueban siempre. La prueba del motor (bajar del átomo a los quarks
con el autopiloto) necesita OpenGL: si no hay, se salta.
"""
import json
import re
from pathlib import Path

import pytest

from atomicworld import atoms
from atomicworld.repository import IsotopeTable, PeriodicTable
from ui import settings
from ui.i18n import LANGUAGES, LOCALES_DIR, Translator

np = pytest.importorskip("numpy")

from viewer import scale  # noqa: E402
from atomicworld.scene import nucleus as nuc  # noqa: E402
from atomicworld.scene import orbitals  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TABLE = PeriodicTable()
ISOTOPES = IsotopeTable()


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return len(value)
    return "text"


def placeholders(value):
    if isinstance(value, dict):
        return {k: placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [placeholders(v) for v in value]
    if not isinstance(value, str):
        return value
    # {element} y {of_element} son el mismo dato: "Iron atom" / "Átomo de hierro" / "Àtom d'or"
    return sorted({p.replace("of_element", "element") for p in re.findall(r"\{(\w+)\}", value)})


# --- Textos ------------------------------------------------------------------------

def locale(lang):
    return json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("lang", ["es", "ca"])
def test_locales_have_the_same_keys_and_parameters(lang):
    assert shape(locale(lang)) == shape(locale("en"))
    assert placeholders(locale(lang)) == placeholders(locale("en"))


def test_every_literal_key_used_in_the_viewer_exists():
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "viewer").rglob("*.py"))
    keys = {k for k in re.findall(r'(?:\.t|\.lines)\("((?:viewer|units)\.[a-z_.]+)"', source)
            if not k.endswith(".")}            # "viewer.levels." + kind: prefijos, no claves
    assert len(keys) > 30
    for lang in LANGUAGES:
        tr = Translator(lang)
        for k in keys:
            assert tr._lookup(k) is not None, f"{lang}: falta {k}"


def test_numbers_follow_the_language():
    assert Translator("en").num(1234.5) == "1,234.50"
    assert Translator("es").num(1234.5) == "1.234,50"
    assert Translator("ca").sci(2.3e17) == "2,3×10¹⁷"


def test_plurals():
    tr = Translator("es")
    assert tr.count(1, "proton") == "1 protón"
    assert tr.count(26, "proton") == "26 protones"


@pytest.mark.parametrize("name, expected", [
    ("Or", "d'or"), ("Hidrogen", "d'hidrogen"), ("Urani", "d'urani"),
    ("Ferro", "de ferro"), ("Iode", "de iode"),
])
def test_catalan_apostrophe(name, expected):
    assert Translator("ca").of(name) == expected


def test_language_cycles_through_all():
    tr = Translator("en")
    assert [tr.next_language() for _ in LANGUAGES] == ["es", "ca", "en"]


def test_settings_are_saved(tmp_path):
    path = tmp_path / "settings.json"
    assert settings.language(path) is None
    settings.save({"language": "ca"}, path)
    assert settings.language(path) == "ca"
    path.write_text("not json")
    assert settings.language(path) is None            # un archivo roto no impide arrancar


# --- Semividas y desintegraciones ------------------------------------------------

@pytest.mark.parametrize("z, a, lang, text", [
    (6, 14, "es", "semivida 5.700 años · se desintegra por β⁻"),
    (27, 60, "en", "half-life 5.27 years · decays by β⁻"),
    (19, 40, "es", "semivida 1,2×10⁹ años · se desintegra por β⁻ (89 %) o β⁺ (11 %)"),
    (26, 56, "ca", "estable"),
])
def test_isotope_summary(z, a, lang, text):
    assert scale.isotope_summary(ISOTOPES.get(z, a), Translator(lang)) == text


def test_every_decay_mode_has_a_text():
    tr = Translator("es")
    for iso in ISOTOPES:
        for m in iso.decay:
            assert scale.decay_mode(m.mode, tr), m.mode


# --- Física de lo que se dibuja ---------------------------------------------------

def test_hydrogen_1s_has_the_right_size():
    r = orbitals.sample_radius(1, 0, 1.0, 200_000, np.random.default_rng(0))
    assert r.mean() == pytest.approx(1.5 * orbitals.BOHR_PM, rel=0.02)   # <r> = 3/2 a₀


def test_radial_functions_have_the_right_number_of_nodes():
    r = np.linspace(0.01, 120, 20000)
    for n in range(1, 8):
        for l in range(min(n, 4)):
            f = orbitals.radial(n, l, 1.0, r)
            nodes = np.sum(np.diff(np.sign(f[np.abs(f) > 1e-12])) != 0)
            assert nodes == n - l - 1, (n, l)


@pytest.mark.parametrize("symbol", ["H", "C", "Fe", "Au", "U", "Og"])
def test_every_electron_gets_points(symbol):
    el = TABLE.find(symbol)
    shells = atoms.subshells(el)
    for didactic in (True, False):
        ppe = orbitals.didactic_points(el.protons, shells) if didactic else \
            orbitals.points_per_electron(el.electrons)
        pts, n, _ = orbitals.sample_atom(el.protons, shells, ppe, didactic, np.random.default_rng(1))
        assert set(n) == {s.n for s in shells}
        assert len(pts) < 400_000


def test_atoms_are_about_the_right_size():
    # el 99 % de la nube, comparado con el radio de van der Waals: mismo orden de magnitud
    for symbol in ("H", "C", "Na", "Fe", "Au", "U"):
        el = TABLE.find(symbol)
        shells = atoms.subshells(el)
        pts, _, _ = orbitals.sample_atom(el.protons, shells, 3000, False, np.random.default_rng(2))
        r99 = np.percentile(np.linalg.norm(pts, axis=1), 99)
        assert 0.5 < r99 / el.vdw_radius_pm < 3.5, symbol


def test_electron_inside_nucleus_is_very_unlikely():
    h = TABLE.find("H")
    p = orbitals.probability_inside_nucleus(1, atoms.subshells(h), atoms.nuclear_radius_fm(1) / 1000)
    assert 1e-15 < p < 1e-13            # (4/3)(R/a₀)³ ≈ 9·10⁻¹⁵


def test_nucleons_are_packed_like_a_liquid_drop():
    a = 56
    centers = nuc.pack_nucleons(a, atoms.nuclear_radius_fm(a), np.random.default_rng(0))
    d = np.linalg.norm(centers[:, None] - centers[None], axis=2) + np.eye(a) * 99
    assert d.min(axis=1).mean() == pytest.approx(nuc.NUCLEON_SPACING_FM, rel=0.1)
    assert np.linalg.norm(centers, axis=1).max() < atoms.nuclear_radius_fm(a)


def test_nuclear_density_is_the_same_for_every_nucleus():
    for a in (4, 56, 238):
        assert 1.5e17 < nuc.density_kg_m3(a, atoms.nuclear_radius_fm(a)) < 3e17


# --- El motor completo (necesita OpenGL) ---------------------------------------------

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


def test_autopilot_goes_from_atom_to_quark_and_back(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("He")
    eng = Engine(gl_context, el, ISOTOPES.default(el), Translator("ca"))

    def fly(mode):
        eng.start_autopilot(mode)
        for _ in range(6000):
            if eng.autopilot is None:
                return eng.level.depth
            eng.update(1 / 60, np.zeros(3), False)
        raise AssertionError(f"autopilot {mode} did not finish")

    assert [fly("down"), fly("down"), fly("down"), fly("up"), fly("up")] == [1, 2, 2, 1, 0]
    assert "quarks" in eng.messages[-3]                 # "Final del viatge: els quarks..."
    eng.render(800, 450)
    assert eng.hud_state(800, 450)["focus"] is not None


def test_changing_isotope_keeps_you_in_the_nucleus(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("C")
    eng = Engine(gl_context, el, ISOTOPES.default(el), Translator("es"))
    eng.start_autopilot("down")
    for _ in range(6000):
        if eng.autopilot is None:
            break
        eng.update(1 / 60, np.zeros(3), False)
    eng.set_atom(el, ISOTOPES.get(6, 14), keep_depth=True)
    assert eng.level.depth == 1 and eng.level.A == 14


# --- Fase 5: orbitales reales p, d y f -------------------------------------------------

@pytest.mark.parametrize("l, k, axis, expected", [
    (1, 0, 0, 3 / 5),          # px: <x²> = 3/5
    (2, 0, 2, 11 / 21),        # dz²: <z²> = 11/21
    (2, 3, 2, 1 / 7),          # dxy: <z²> = 1/7 (está en el plano xy)
    (2, 4, 2, 1 / 7),          # dx²−y²: también en el plano xy
    (3, 0, 2, 23 / 45),        # fz³: <z²> = 23/45
])
def test_orbitals_point_where_their_names_say(l, k, axis, expected):
    d = orbitals.orbital_directions(l, k, 200_000, np.random.default_rng(3))
    assert np.mean(d[:, axis] ** 2) == pytest.approx(expected, abs=0.006)


@pytest.mark.parametrize("l", [1, 2, 3])
def test_full_subshell_is_a_sphere(l):
    """Teorema de Unsöld: los 2l+1 orbitales llenos suman una densidad esférica."""
    rng = np.random.default_rng(4)
    d = np.vstack([orbitals.orbital_directions(l, k, 80_000, rng) for k in range(2 * l + 1)])
    for axis in range(3):
        assert np.mean(d[:, axis] ** 2) == pytest.approx(1 / 3, abs=0.004)
        assert np.mean(d[:, axis] ** 4) == pytest.approx(1 / 5, abs=0.004)


@pytest.mark.parametrize("l, electrons, occupancy", [
    (1, 2, [1, 1, 0]),                    # carbono 2p²: dos desapareados
    (1, 4, [2, 1, 1]),                    # oxígeno 2p⁴
    (2, 6, [2, 1, 1, 1, 1]),              # hierro 3d⁶: 4 desapareados (por eso es magnético)
    (3, 7, [1] * 7),                      # gadolinio 4f⁷: 7 desapareados
    (3, 14, [2] * 7),
])
def test_hund_rule(l, electrons, occupancy):
    assert orbitals.hund_occupancy(l, electrons) == occupancy


def test_every_orbital_has_a_name():
    assert [len(orbitals.orbital_names(l)) for l in range(4)] == [1, 3, 5, 7]


def test_one_subshell_or_one_orbital_alone():
    fe = TABLE.find("Fe")
    shells = atoms.subshells(fe)
    i = next(i for i, s in enumerate(shells) if s.name == "3d")
    pts, owner = orbitals.sample_subshell(26, shells, i, 1000, True, np.random.default_rng(5))
    assert len(pts) == 6000 and sorted(set(owner)) == [0, 1, 2, 3, 4]
    pts, owner = orbitals.sample_subshell(26, shells, i, 1000, True, np.random.default_rng(5), only=3)
    assert len(pts) == 1000 and set(owner) == {3}


def test_keys_o_and_i_walk_through_subshells_and_orbitals(gl_context):
    from viewer.engine import Engine
    el = TABLE.find("Fe")
    eng = Engine(gl_context, el, ISOTOPES.default(el), Translator("es"))
    seen = []
    for _ in range(len(atoms.subshells(el)) + 1):
        eng.cycle_subshell()
        seen.append(None if eng.root.view is None else eng.root.subshell_label(eng.root.view))
    assert seen == ["4s²", "3d⁶", "3p⁶", "3s²", "2p⁶", "2s²", "1s²", None]
    eng.cycle_subshell(); eng.cycle_subshell()                     # 3d⁶
    labels = []
    for _ in range(6):
        eng.cycle_orbital()
        labels.append(eng.root.orbital_label() if eng.root.orbital is not None else None)
    assert labels == ["3dz²", "3dxz", "3dyz", "3dxy", "3dx²−y²", None]
    eng.cycle_orbital()
    focus = eng.hud_state(800, 450)["focus"]
    assert focus.title == "Orbital 3dz² · 2 electrones" and "[dz² ↑↓]" in focus.detail
    eng.toggle_mode()                                              # realista: sin orbitales sueltos
    assert eng.root.orbital is None and eng.root.view is not None
    eng.render(800, 450)


# --- Fase 6: resumen para el visor web ---------------------------------------------------

def test_describe_atom_is_small_json_and_matches_the_desktop_viewer():
    from atomicworld.scene.describe import describe_atom
    og = TABLE.find("Og")
    d = describe_atom(og, ISOTOPES.default(og))
    assert len(json.dumps(d)) < 60_000                       # el átomo más grande cabe en ~50 kB
    fe = TABLE.find("Fe")
    d = describe_atom(fe, ISOTOPES.default(fe))
    rng = np.random.default_rng(26 * 1000 + 56)              # misma semilla que el visor de escritorio
    centers = nuc.pack_nucleons(56, atoms.nuclear_radius_fm(56), rng)
    assert np.allclose(d["nucleus"]["centers_fm"], centers, atol=1e-3)
    shells = atoms.subshells(fe)
    assert d["atom"]["view_distance_pm"] == pytest.approx(orbitals.atom_view_distance(fe.vdw_radius_pm, 26, shells), rel=1e-4)
    # la tabla de radios reproduce el radio medio del orbital
    s4 = next(s for s in d["atom"]["subshells"] if s["name"] == "4s")
    q = np.array(s4["radius_quantiles_pm"])
    assert np.mean((q[1:] + q[:-1]) / 2) == pytest.approx(s4["mean_radius_pm"], rel=0.05)
