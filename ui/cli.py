"""Interfaz de consola de AtomicWorld, en inglés, castellano y catalán.

Es el ÚNICO módulo con print() e input(). Pide datos, llama al núcleo (atomicworld) y
muestra los resultados. Los textos salen de ui/locales/ (sección "console"); los errores
del núcleo llegan como códigos (FormulaError.code, UnitError.code) y se traducen aquí,
igual que hace la web.
"""
from atomicworld import bigbang, names
from atomicworld import nucleosynthesis as nuc
from atomicworld import units
from atomicworld.chemistry import FormulaError, MoleculeAnalysis, analyze, validate_formula
from atomicworld.repository import IsotopeTable, ParticleCatalog, PeriodicTable

from . import colors as c
from . import launcher, settings
from .i18n import LANGUAGES, Translator, language_names

tr = Translator()


def T(key: str, **params) -> str:
    """Texto de la consola en el idioma actual."""
    return tr.t(f"console.{key}", **params)


def error_text(exc) -> str:
    """Error del núcleo (con código) -> frase en el idioma actual."""
    code = getattr(exc, "code", None)
    params = dict(getattr(exc, "params", {}) or {})
    if isinstance(params.get("symbols"), list):
        params["symbols"] = ", ".join(params["symbols"])
    text = tr.t(f"errors.{code}", **params) if code else ""
    return text if text and text != f"errors.{code}" else str(exc)


# --- Utilidades de entrada ---------------------------------------------------

def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_int(prompt: str, minimum: int = 1) -> int:
    while True:
        text = ask(prompt)
        try:
            value = int(text)
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(c.paint("  " + T("input.whole_number", minimum=minimum), c.RED))


def parse_number(text: str) -> float:
    """Acepta 18,5 y 18.5 (y 1.000,5 / 1,000.5 en el idioma actual)."""
    text = text.replace(" ", "")
    if tr.dec == "," and "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "") if text.count(",") and "." in text else text.replace(",", ".")
    return float(text)


def ask_float(prompt: str) -> float:
    while True:
        try:
            value = parse_number(ask(prompt))
            if value > 0:
                return value
        except ValueError:
            pass
        print(c.paint("  " + T("input.positive_number"), c.RED))


def fmt(value: float) -> str:
    """Notación científica legible: 6.022e+23 -> 6.022 × 10^23 (6,022 en castellano)."""
    if value == 0:
        return "0"
    mantissa, exponent = f"{value:.4e}".split("e")
    mantissa = mantissa.replace(".", tr.dec)
    exp = int(exponent)
    return mantissa if exp == 0 else f"{mantissa} × 10^{exp}"


def invalid_option() -> None:
    print(c.paint(T("menu.invalid"), c.RED))


# --- Idioma --------------------------------------------------------------------

def choose_language() -> None:
    """Se pregunta la primera vez y desde el menú principal. Se guarda para la próxima."""
    langs = language_names()
    print("\n    Language · Idioma · Idioma")
    for i, lang in enumerate(LANGUAGES, start=1):
        print(f"     {i}] {langs[lang]}")
    while True:
        answer = ask("    > ").lower()
        choice = None
        if answer.isdigit() and 1 <= int(answer) <= len(LANGUAGES):
            choice = LANGUAGES[int(answer) - 1]
        elif answer in LANGUAGES:
            choice = answer
        else:
            choice = next((l for l, n in langs.items() if n.lower() == answer), None)
        if choice:
            tr.set_language(choice)
            settings.save({"language": choice})
            print(c.paint("    " + T("language.saved"), c.GREEN))
            return
        print(c.paint("    1, 2, 3?", c.RED))


# --- Tabla periódica ---------------------------------------------------------

def show_periodic_table(table: PeriodicTable) -> None:
    print(f"\n{c.BOLD}{T('table.title'):^80}{c.RESET}\n")
    width = max(len(tr.element(el.number)) for el in table) + 1
    cells = [f"{el.number:>3}. {tr.element(el.number):<{width}}" for el in table]
    per_row = 4 if width <= 14 else 3
    for i in range(0, len(cells), per_row):
        print("   " + "".join(cells[i:i + per_row]))


def print_analysis(result: MoleculeAnalysis) -> None:
    print(f"\n{c.BOLD}{result.formula}{c.RESET} — {tr.num(result.grams, 4).rstrip('0').rstrip(tr.dec)} g")
    print(f"  {T('molecule.molar_mass'):<11}: {tr.num(result.molar_mass, 4)} g/mol")
    print(f"  {T('molecule.moles'):<11}: {fmt(result.moles)} mol")
    print(f"  {T('molecule.molecules'):<11}: {fmt(result.molecules)}")
    print(f"  {T('molecule.atoms'):<11}: {fmt(result.total_atoms)}")

    print(f"\n{c.rainbow_title(T('molecule.subatomic'))}")
    for e in result.elements:
        el = e.element
        sub = e.count_in_formula if e.count_in_formula > 1 else ""
        print(f"\n  {c.BOLD}{tr.element(el.number)} ({el.symbol}{sub}){c.RESET}")
        for label, value in (("atoms", e.atoms), ("protons", e.protons), ("neutrons", e.neutrons),
                             ("electrons", e.electrons)):
            print(f"    {T('molecule.' + label):<10}: {fmt(value)}")
        up, down = c.paint("Up", c.GREEN), c.paint("Down", c.GREEN)
        print("    " + T("molecule.quarks_in", quark=up, protons=fmt(e.up_in_protons),
                            neutrons=fmt(e.up_in_neutrons)))
        print("    " + T("molecule.quarks_in", quark=down, protons=fmt(e.down_in_protons),
                            neutrons=fmt(e.down_in_neutrons)))
        print("    " + T("molecule.quark_mass", quark=up, mass=fmt(e.up_mass_mev)))
        print("    " + T("molecule.quark_mass", quark=down, mass=fmt(e.down_mass_mev)))

    pct = result.quark_mass_fraction * 100
    print(f"\n  {c.BOLD}{T('molecule.mass_title')}{c.RESET}")
    for line in tr.lines("console.molecule.mass_explanation", pct=tr.num(pct, 2), rest=tr.num(100 - pct, 2)):
        print("    " + line)
    print("\n  " + T("molecule.average_note"))


def molecule_calculator(table: PeriodicTable, particles: ParticleCatalog) -> None:
    print("\n" + T("molecule.intro"))
    while True:
        formula = ask(T("molecule.ask_formula"))
        if not formula:
            return
        try:
            validate_formula(formula, table)       # validar antes de pedir los gramos
        except FormulaError as exc:
            print(c.paint("  " + error_text(exc), c.RED))
            continue
        grams = ask_float(T("molecule.ask_grams"))
        try:
            print_analysis(analyze(formula, grams, table, particles))
        except ValueError as exc:                  # FormulaError también es ValueError
            print(c.paint("  " + error_text(exc), c.RED))
        print()


def explore_atom(table: PeriodicTable) -> None:
    """Pide un elemento y un isótopo y abre el visor 3D en otra ventana."""
    problem = launcher.missing_dependencies()
    if problem:
        print(c.paint("  " + T("explore.missing", packages=problem), c.RED))
        print("  " + T("explore.install"))
        return
    text = ask(T("explore.ask_element"))
    if not text:
        return
    try:
        el = table.find(text)
    except ValueError:
        print(c.paint("  " + T("explore.unknown_element", text=text), c.RED))
        return
    isotopes = IsotopeTable()
    natural = isotopes.natural(el.number)
    known = isotopes.of(el.number)
    name = tr.element(el.number)
    print(f"\n  {c.BOLD}{name} ({el.symbol}){c.RESET} — "
          + T("explore.known", count=len(known), first=known[0].a, last=known[-1].a))
    if natural:
        print("  " + T("explore.natural"))
        for iso in natural:
            print(f"    {el.symbol}-{iso.a:<4} {tr.num(iso.abundance, 4):>9} %   "
                  f"({tr.count(iso.neutrons, 'neutron')})")
    else:
        print(c.paint("  " + T("explore.none_natural"), c.YELLOW))
    default = isotopes.default(el)
    while True:
        answer = ask(T("explore.ask_isotope", isotope=f"{el.symbol}-{default.a}"))
        if not answer:
            iso = default
            break
        try:
            iso = isotopes.get(el.number, int(answer))
            break
        except ValueError:
            print(c.paint("  " + T("explore.unknown_isotope", isotope=f"{el.symbol}-{answer}",
                                   first=known[0].a, last=known[-1].a), c.RED))
    launcher.open_viewer(el, iso, tr.lang)
    print(c.paint("  " + T("explore.opening", isotope=f"{el.symbol}-{iso.a}"), c.GREEN))
    print("  " + T("explore.hint"))


def periodic_table_menu(table: PeriodicTable, particles: ParticleCatalog) -> None:
    while True:
        show_periodic_table(table)
        print(f"""
            [0] {T('menu.back')}
             1] {T('table.molecule')}
             2] {T('table.explore')}
        """)
        option = ask(T("menu.select"))
        if option == "0":
            return
        elif option == "1":
            molecule_calculator(table, particles)
        elif option == "2":
            explore_atom(table)
        else:
            invalid_option()


# --- Modelo Estándar y Big Bang ---------------------------------------------

def particle_name(p) -> str:
    return tr.particle(p.name)


def family_name(family: str) -> str:
    return names.family(family, tr.lang)


def show_standard_model(catalog: ParticleCatalog) -> None:
    print(f"\n{'':>35}{c.rainbow_title(T('model.title'))}\n")
    width = max(len(particle_name(p)) for p in catalog) + 1
    cells = [f"{i:02}. " + c.paint_family(f"{particle_name(p):<{width}}", p.family)
             for i, p in enumerate(catalog)]
    for i in range(0, len(cells), 3):
        print("   " + "  ".join(cells[i:i + 3]))
    families = list(c.FAMILY_COLORS)
    print(f"\n   [{T('model.key')}]  " + "   ".join(c.paint_family(family_name(f), f) for f in families))


def format_mass(mev: float) -> str:
    if mev == 0:
        return "0"
    if mev < 1e-3:
        return f"{mev * 1e6:.3g}".replace(".", tr.dec) + " eV/c²"
    if mev < 1000:
        return f"{mev:.6g}".replace(".", tr.dec) + " MeV/c²"
    return f"{mev / 1000:.6g}".replace(".", tr.dec) + " GeV/c²"


def show_particle(catalog: ParticleCatalog) -> None:
    text = ask(T("model.ask_particle"))
    if not text:
        return
    try:
        p = catalog.particles[int(text)] if text.isdigit() else catalog.find(text)
    except (IndexError, ValueError):
        print(c.paint("  " + T("model.unknown_particle"), c.RED))
        return
    prefix = "< " if p.mass_is_upper_limit else ""
    print(f"\n  {c.paint_family(particle_name(p), p.family)}  ({family_name(p.family)})")
    print(f"    {T('model.mass'):<7}: {prefix}{format_mass(p.mass_mev)}")
    if p.mass_mev > 0:
        print(f"    {'':<7}  {prefix}{fmt(units.mev_to_kg(p.mass_mev))} kg"
              f" = {prefix}{fmt(units.from_mev(p.mass_mev, 'u'))} u")
    print(f"    {T('model.charge'):<7}: {p.charge} e")
    print(f"    {T('model.spin'):<7}: {p.spin}")
    print(f"    {T('model.binary'):<7}: {p.binary}")
    if p.mass_is_upper_limit:
        print("    " + T("model.upper_limit"))
    if p.hypothetical:
        print("    " + T("model.hypothetical"))


def show_particle_masses(catalog: ParticleCatalog) -> None:
    """Lo que hacía StandardModelConversor.py: todas las masas pasadas a kilogramos."""
    width = max(len(particle_name(p)) for p in catalog) + 2
    print(f"\n  {T('masses.particle'):<{width}}{T('masses.mass'):>18}{T('masses.mass_kg'):>24}"
          f"{T('masses.mass_u'):>24}")
    for row in units.particle_masses(catalog):
        p = row.particle
        name = c.paint_family(f"{particle_name(p):<{width}}", p.family)
        if row.is_massless:
            print(f"  {name}{T('masses.massless'):>18}{'0':>24}{'0':>24}")
            continue
        prefix = "< " if p.mass_is_upper_limit else ""
        print(f"  {name}{prefix + format_mass(p.mass_mev):>18}"
              f"{prefix + fmt(row.mass.kg):>24}{prefix + fmt(row.mass.to('u')):>24}")
    print("\n  " + T("masses.footnote"))


def ask_unit(prompt: str) -> str:
    options = list(units.UNITS_IN_MEV)
    labels = ", ".join(units.symbol(u) for u in options)
    while True:
        text = ask(f"{prompt} ({labels}): ").replace("/c²", "").replace("/c2", "")
        match = next((u for u in options if u.lower() == text.lower()), None)
        if match:
            return match
        print(c.paint("  " + tr.t("errors.unknown_unit", unit=text), c.RED))


def mass_converter(catalog: ParticleCatalog) -> None:
    while True:
        text = ask("\n" + T("masses.ask_value"))
        if not text:
            return
        try:
            mass = units.Mass.of(parse_number(text), ask_unit(T("masses.unit")))
        except ValueError as exc:
            print(c.paint("  " + error_text(exc), c.RED))
            continue
        print()
        for unit, value in mass.all_units().items():
            print(f"    {fmt(value):>22} {units.symbol(unit)}")
        print("\n    " + T("masses.compare", electrons=fmt(mass.electron_masses),
                              protons=fmt(mass.proton_masses)))
        closest = units.closest_particle(mass, catalog)
        if closest:
            particle, ratio = closest
            name = c.paint_family(particle_name(particle), particle.family)
            print("    " + T("masses.closest", name=name, ratio=f"{ratio:.3g}".replace(".", tr.dec)))


def mass_menu(catalog: ParticleCatalog) -> None:
    while True:
        print(f"""
            {T('masses.title')}
            [0] {T('menu.back')}
             1] {T('masses.option_table')}
             2] {T('masses.option_convert')}
        """)
        option = ask(T("menu.what"))
        if option == "0":
            return
        elif option == "1":
            show_particle_masses(catalog)
        elif option == "2":
            mass_converter(catalog)
        else:
            invalid_option()


def print_bigbang(result: bigbang.BigBangResult, title: str) -> None:
    print(f"\n[ {T('bigbang.byte')} ]  {title}\n")
    coloured_bytes, found_names = [], []
    for m in result.matches:
        if m.particle:
            coloured_bytes.append(c.paint_family(m.byte, m.particle.family))
            found_names.append(c.paint_family(particle_name(m.particle), m.particle.family))
        else:
            coloured_bytes.append(m.byte)
            found_names.append(m.byte)
    print(T("bigbang.matched_bytes") + "\n")
    print(":".join(coloured_bytes))
    print("\n" + T("bigbang.matched_names") + "\n")
    print(":".join(found_names))
    extra = T("bigbang.leftover", count=result.leftover_bits) if result.leftover_bits else ""
    print("\n" + T("bigbang.summary", full=result.full_bytes, extra=extra, found=len(result.found)))


def bigbang_menu(catalog: ParticleCatalog) -> None:
    n = ask_int(T("bigbang.ask_bits"))
    bits, durations = bigbang.generate_bits_timed(n)
    print_bigbang(bigbang.match_particles(bits, catalog), T("bigbang.original"))

    options = list(bigbang.TRANSFORMS.items())
    while True:
        print(f"\n            [0] {T('menu.back')}")
        print(f"             1] {T('bigbang.option_time')}")
        for i, (key, _) in enumerate(options, start=2):
            print(f"             {i}] {T('bigbang.transforms.' + key)}")
        choice = ask(T("bigbang.ask_option"))

        if choice == "0":
            return
        if choice == "1":
            total = sum(durations)
            print("\n" + T("bigbang.total_time", total=tr.int(total),
                           average=tr.num(total / len(durations), 1)))
            for i, (bit, ns) in enumerate(zip(bits[:16], durations[:16]), start=1):
                print("  " + T("bigbang.bit_time", i=f"{i:>3}", bit=bit, ns=ns))
            if len(bits) > 16:
                print("  " + T("bigbang.more", count=len(bits) - 16))
            continue
        try:
            key, (_label, fn) = options[int(choice) - 2]
        except (ValueError, IndexError):
            print(c.paint(T("bigbang.invalid"), c.RED))
            continue
        print_bigbang(bigbang.match_particles(fn(bits), catalog), T("bigbang.transforms." + key))


def standard_model_menu(catalog: ParticleCatalog) -> None:
    while True:
        show_standard_model(catalog)
        print(f"""
            [0] {T('menu.back')}
             1] {T('model.option_bigbang')}
             2] {T('model.option_particle')}
             3] {T('model.option_masses')}
        """)
        option = ask(T("menu.what"))
        if option == "0":
            return
        elif option == "1":
            bigbang_menu(catalog)
        elif option == "2":
            show_particle(catalog)
        elif option == "3":
            mass_menu(catalog)
        else:
            invalid_option()


# --- Los tres primeros minutos (nucleosíntesis) -----------------------------------

def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds:.3g}".replace(".", tr.dec) + " s"
    if seconds < 60:
        return f"{seconds:.1f}".replace(".", tr.dec) + " s"
    if seconds < 3600:
        m, s = divmod(round(seconds), 60)
        return f"{m} min {s:02} s"
    h, rem = divmod(round(seconds), 3600)
    return f"{h} h {rem // 60:02} min"


def sci_k(kelvin: float) -> str:
    return f"{kelvin:.2e}".replace(".", tr.dec)


def composition_bar(neutrons: float, deuterium: float, helium: float, width: int = 40) -> str:
    """Barra apilada: neutrones (n), protones (p), deuterio (D) y helio (He)."""
    n = round(neutrons * width)
    he = round(helium * width)
    d = round(deuterium * width)
    p = max(width - n - he - d, 0)
    return (c.paint("n" * n, c.MAGENTA) + c.paint("p" * p, c.CYAN)
            + c.paint("D" * d, c.YELLOW) + c.paint("█" * he, c.GREEN))


def timeline_rows(result: nuc.NucleosynthesisResult):
    """Fotogramas de Weinberg y momentos clave, ya traducidos y ordenados en el tiempo."""
    rows = [(T("universe.frame", n=i), "", result.at_temperature(k / nuc.MEV_TO_KELVIN))
            for i, k in enumerate(nuc.WEINBERG_FRAMES_K.values(), start=1)]
    rows += [(T(f"universe.event_names.{e.name}"), tr.t(f"events.{e.name}"), e.snapshot)
             for e in result.events if e.name != "deuterium_peak"]
    return sorted(rows, key=lambda r: r[2].time_s)


def print_nucleosynthesis(result: nuc.NucleosynthesisResult) -> None:
    print(f"\n{c.rainbow_title(T('universe.title'))}")
    print("  " + T("universe.parameters", eta=f"{result.eta:.2e}".replace(".", tr.dec),
                   species=f"{result.neutrino_species:g}".replace(".", tr.dec),
                   tau=f"{result.neutron_lifetime_s:g}".replace(".", tr.dec)) + "\n")
    rows = timeline_rows(result)
    w = max(len(title) for title, _, _ in rows) + 1        # los títulos cambian de largo con el idioma
    print(f"  {'':<{w}}{T('universe.time'):>12}{T('universe.temperature'):>14}{'':>11}  "
          f"{T('universe.neutrons'):>9}   {T('universe.composition')}")
    for title, description, s in rows:
        is_event = bool(description)
        name = c.paint(f"{title:<{w}}", c.YELLOW if is_event else c.BOLD)
        print(f"  {name}{fmt_time(s.time_s):>12}{sci_k(s.temperature_k):>12} K"
              f"{tr.num(s.temperature_mev, 3):>9} MeV{tr.num(s.neutron_fraction * 100, 1):>8} %   "
              f"{composition_bar(s.neutron_fraction, s.deuterium_fraction, s.helium_fraction)}")
        if is_event:
            print(f"  {'':<{w}}{c.paint('↳ ' + description, c.YELLOW)}")
    print(f"\n  [{T('model.key')}] {c.paint('n', c.MAGENTA)} {T('universe.key_neutrons')}  "
          f"{c.paint('p', c.CYAN)} {T('universe.key_protons')}  {c.paint('D', c.YELLOW)} "
          f"{T('universe.key_deuterium')}  {c.paint('█', c.GREEN)} {T('universe.key_helium')}")

    pct = lambda x: tr.num(x * 100, 1)
    print(f"\n  {c.BOLD}{T('universe.result')}{c.RESET}")
    print("    " + T("universe.helium", value=pct(result.helium_fraction),
                       observed=pct(nuc.OBSERVED_HELIUM), standard=pct(nuc.STANDARD_BBN_HELIUM)))
    print("    " + T("universe.hydrogen", value=pct(result.hydrogen_fraction)))
    print("    " + T("universe.deuterium", value=f"{result.deuterium_to_hydrogen:.1e}".replace(".", tr.dec),
                       observed=f"{nuc.OBSERVED_D_TO_H:.2e}".replace(".", tr.dec)))


def ask_float_default(prompt: str, default: float, minimum: float, maximum: float) -> float:
    g = lambda v: f"{v:g}".replace(".", tr.dec)
    while True:
        text = ask(f"{prompt} [{g(default)}]: ")
        if not text:
            return default
        try:
            value = parse_number(text)
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(c.paint("  " + T("input.between", minimum=g(minimum), maximum=g(maximum)), c.RED))


def custom_universe() -> None:
    print("\n" + T("universe.custom_intro"))
    eta = ask_float_default("  " + T("universe.ask_eta"), nuc.DEFAULT_ETA * 1e10, 0.1, 100) * 1e-10
    species = ask_float_default("  " + T("universe.ask_species"), nuc.DEFAULT_NEUTRINO_SPECIES, 0, 10)
    tau = ask_float_default("  " + T("universe.ask_tau"), nuc.DEFAULT_NEUTRON_LIFETIME_S, 1, 1e6)
    print_nucleosynthesis(nuc.simulate(eta, tau, species))


def compare_neutrinos() -> None:
    print()
    for line in tr.lines("console.universe.neutrinos_intro"):
        print(line)
    print(f"\n  {T('universe.species'):>8}   {T('universe.helium_short'):>7}")
    for n in range(1, 6):
        y = nuc.simulate(neutrino_species=n).helium_fraction
        mark = c.paint("  ← " + T("universe.compatible"), c.GREEN) \
            if abs(y - nuc.OBSERVED_HELIUM) < 0.006 else ""
        print(f"  {n:>8}   {tr.num(y * 100, 1):>6} %{mark}")
    print("\n  " + T("universe.lep"))


def particle_by_particle() -> None:
    n = ask_int(T("universe.ask_nucleons"), minimum=4)
    if n > 1_000_000:
        print(c.paint("  " + T("universe.capped"), c.YELLOW))
        n = 1_000_000
    counts = nuc.simulate_particles(n)
    checkpoints = [1e11, 1e10, 3e9, 1e9, 5e8, 1e8]
    print(f"\n  {T('universe.time'):>12}{T('universe.temperature'):>14}  {T('universe.neutrons'):>9}"
          f"{T('universe.protons'):>9}{T('universe.helium_short'):>10}")
    for k in checkpoints:
        row = min(counts, key=lambda r: abs(r.temperature_mev - k / nuc.MEV_TO_KELVIN))
        print(f"  {fmt_time(row.time_s):>12}{sci_k(nuc.kelvin(row.temperature_mev)):>12} K"
              f"  {row.neutrons:>9}{row.protons:>9}{row.helium_nuclei:>10}")
    last = counts[-1]
    print("\n  " + T("universe.your_universe", helium=last.helium_nuclei, hydrogen=last.protons,
                       pct=tr.num(last.helium_fraction * 100, 1)))
    print("  " + T("universe.run_again"))


def nucleosynthesis_menu() -> None:
    while True:
        print(f"""
            {T('universe.menu_title')}
            [0] {T('menu.back')}
             1] {T('universe.option_simulate')}
             2] {T('universe.option_custom')}
             3] {T('universe.option_particles')}
             4] {T('universe.option_neutrinos')}
        """)
        option = ask(T("menu.what"))
        if option == "0":
            return
        elif option == "1":
            print_nucleosynthesis(nuc.simulate())
        elif option == "2":
            custom_universe()
        elif option == "3":
            particle_by_particle()
        elif option == "4":
            compare_neutrinos()
        else:
            invalid_option()


# --- Menú principal ------------------------------------------------------------

def run() -> None:
    saved = settings.language()
    if saved in LANGUAGES:
        tr.set_language(saved)
    table = PeriodicTable()
    particles = ParticleCatalog()
    try:
        if saved not in LANGUAGES:
            choose_language()                # la primera vez
        while True:
            print(f"""
                    {c.BOLD}Atomic World{c.RESET}
                [0] {T('main.exit')}
                    1] {T('main.table')}
                    2] {T('main.model')}
                    3] {T('main.universe')}
                    4] Language · Idioma
            """)
            option = ask(T("menu.select"))
            if option == "0":
                break
            elif option == "1":
                periodic_table_menu(table, particles)
            elif option == "2":
                standard_model_menu(particles)
            elif option == "3":
                nucleosynthesis_menu()
            elif option == "4":
                choose_language()
            else:
                invalid_option()
    except (KeyboardInterrupt, EOFError):
        print()
    print(T("main.goodbye"))
