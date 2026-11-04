# AtomicWorld 👨‍🏫

De la molécula a los quarks, y de los quarks al Big Bang:

1. **Tabla periódica**: calcula moles, moléculas, átomos, protones, neutrones,
   electrones y quarks de cualquier sustancia (`H2O`, `C6H12O6`, `Ca(OH)2`...), y
   **explora en 3D** cualquier átomo de cualquier isótopo: de la nube de electrones al
   núcleo, a los protones y neutrones y a sus quarks.
2. **Modelo Estándar**: fichas de todas las partículas, conversor de masas
   (eV/c² ⇄ kg ⇄ u) y el juego clásico del "Big Bang" de bits.
3. **Los tres primeros minutos**: simulación física de la nucleosíntesis primordial,
   inspirada en el libro de Steven Weinberg.

Este repositorio es el **núcleo** (datos, cálculos y consola). La **web** está en su propio
repositorio, `atomicworld_web`, que usa este como paquete de Python (`pyproject.toml`):

```bash
pip install -e ../../AtomicWorld     # desde project-AtomicWorld/atomicworld_web/atomicworld
```

## Uso

```bash
pip install -r requirements.txt
python main.py          # ejecutar el programa
python -m pytest        # ejecutar los tests
```

Requiere Python 3.10 o superior.

**Idiomas:** todo el programa (menús, resultados y visor 3D) está en inglés, castellano y catalán.
La primera vez pregunta el idioma y lo guarda en `~/.atomicworld/settings.json`; se cambia con la
opción **4] Language · Idioma** del menú principal (o con la tecla **L** dentro del visor). Los
números siguen el idioma: `6.022 × 10^23` en inglés, `6,022 × 10^23` en castellano y catalán,
y al escribir se aceptan tanto `18,5` como `18.5`.

## Visor 3D

Viaje en primera persona dentro de un átomo, adaptado del *Microscopio de ADN*. Se abre desde
el menú (**Periodic Table → 2] Explore an atom in 3D**) o directamente:

```bash
python -m viewer Fe                       # hierro-56, el isótopo más abundante
python -m viewer Uranio --isotope 235     # nombre en cualquier idioma, símbolo o número
python -m viewer 6 --isotope 14 --lang ca --realistic
```

| Nivel | Escala | Qué se ve |
|---|---|---|
| 1 · Átomo | pm | la nube de electrones, capa a capa; el núcleo, a su tamaño real |
| 2 · Núcleo | fm | protones y neutrones (didáctico) o densidad nuclear (realista) |
| 3 · Nucleón | 0,1 fm | quarks de valencia, tubo de gluones en Y y mar de partones |

| Tecla | Acción |
|---|---|
| Clic / Esc | capturar / soltar el ratón (Esc otra vez: salir) |
| W A S D · Espacio / Ctrl | moverse · subir / bajar |
| Q / E · Shift · Rueda | girar · turbo ×5 · multiplicador de velocidad |
| **Enter / Retroceso** | **piloto automático**: bajar al siguiente nivel / volver al anterior |
| **N / P** | elemento siguiente / anterior |
| **[ / ]** | isótopo anterior / siguiente (los ~3.500 conocidos) |
| **O** | ver los subniveles de uno en uno (4s → 3d → 3p...), con ejes x, y, z; la nave se acerca sola |
| **I** | con un subnivel p, d o f elegido: sus orbitales de uno en uno (3dz², 3dxz...) |
| Tab | modo didáctico ↔ realista |
| **L** | idioma: English → español → català (se recuerda) |
| H · F11 | ayuda · pantalla completa |

**Física:** orbitales hidrogenoides con la carga efectiva de Slater (`atomicworld/atoms.py`),
escalados al tamaño medio de los orbitales de Slater (con su n efectivo); así el radio del 99 % de la
nube queda entre 0,6 y 2 veces el radio atómico de Rahm en los 118 elementos. Núcleo de radio
1,2 fm·A^(1/3) con nucleones a ~1,75 fm (densidad ~2,3·10¹⁷ kg/m³) o perfil de Woods–Saxon; quarks
con las masas de `particles.json`.

En modo didáctico cada orbital tiene su forma real: los 3 p, los 5 d y los 7 f, muestreados de
sus armónicos esféricos reales |Y_lm|² y ocupados según la **regla de Hund** (el HUD los dibuja
como casillas: `dz² ↑↓ · dxz ↑ · dyz ↑ · dxy ↑ · dx²−y² ↑` en el hierro). Un subnivel lleno sale
esférico sin forzarlo (**teorema de Unsöld**: los tests lo comprueban hasta el cuarto momento).
Con un subnivel a medio llenar hay varios estados igual de buenos (en un átomo aislado ninguna
orientación es especial): se muestra uno de ellos. En la vista de todos los electrones, las capas
internas se atenúan para que se vean las externas; con **O** cada subnivel se genera aparte, con
150.000 puntos y un color por orbital.

**Limitaciones:** átomo aislado; sin efectos relativistas (importantes en los electrones internos
de los átomos pesados); núcleo como gota líquida, sin capas; el movimiento de los quarks y el tubo
en Y son una ilustración: la QCD no tiene trayectorias.

`tools/viewer_render_test.py` hace el viaje completo sin ventana y guarda capturas PNG.

**En la web:** la herramienta *Átomo en 3D* de `atomicworld_web` es el mismo visor escrito en
JavaScript (WebGL 2). La física no se duplica: `atomicworld/scene/describe.py` resume el átomo
(tablas de radios de cada subnivel, casillas de Hund, posiciones de los nucleones...) en unos
pocos kB, y el navegador solo sortea puntos con esas tablas.

**Gráfica NVIDIA en Windows:** Configuración → Sistema → Pantalla → Gráficos → añade el
`python.exe` de tu entorno → Alto rendimiento. Al arrancar, la consola dice qué GPU se usa.

## Estructura

```
AtomicWorld/
├── main.py                  Punto de entrada
├── atomicworld/             NÚCLEO: datos + lógica (sin print ni input)
│   ├── constants.py         Avogadro, quarks por nucleón...
│   ├── models.py            Clases Element, Isotope y Particle
│   ├── repository.py        Carga los JSON y hace búsquedas (en cualquier idioma)
│   ├── names.py             Nombres de elementos y partículas en inglés, castellano y catalán
│   ├── atoms.py             Configuración electrónica, reglas de Slater y radio del núcleo
│   ├── scene/               Física de los visores 3D (necesita NumPy: pip install atomicworld[scene])
│   │   ├── orbitals.py      Nubes de electrones, orbitales reales p/d/f, regla de Hund
│   │   ├── nucleus.py       Empaquetado de nucleones, Woods–Saxon
│   │   └── describe.py      Resumen de un átomo para el visor web (/api/atom de atomicworld_web)
│   ├── chemistry.py         Fórmula → moles → átomos → quarks
│   ├── units.py             Conversor de masas: eV/c², u, g y kg
│   ├── bigbang.py           Juego de bits, transformaciones y coincidencias
│   ├── nucleosynthesis.py   Los tres primeros minutos: n/p, deuterio y helio
│   └── data/
│       ├── elements.json    Tabla periódica
│       ├── isotopes.json    Los ~3.500 isótopos conocidos
│       ├── particles.json   Modelo Estándar
│       └── names/           en.json, es.json, ca.json
├── ui/                      PRESENTACIÓN (escritorio)
│   ├── colors.py            Colores de consola
│   ├── cli.py               Menús de consola
│   ├── launcher.py          Abre el visor 3D en otro proceso
│   ├── i18n.py              Traductor: textos, plurales, números y "de/d'" en catalán
│   ├── settings.py          Idioma guardado (~/.atomicworld/settings.json)
│   └── locales/             en.json, es.json, ca.json (consola, visor, errores del núcleo)
├── viewer/                  VISOR 3D (numpy, moderngl, pyglet, pillow)
│   ├── __main__.py          python -m viewer Fe --isotope 56 --lang es
│   ├── app.py               Ventana, teclas y ratón
│   ├── engine.py            Pila de niveles, transiciones y piloto automático
│   ├── ship.py · hud.py     Nave con velocidad logarítmica · HUD
│   ├── levels/              atom.py, nucleus.py, nucleon.py
│   └── render/              Puntos, líneas y shaders
├── tests/                   Tests automáticos (pytest)
├── tools/                   build_data.py, viewer_render_test.py, convert_legacy.py
└── legacy/                  Script original, como referencia
```

**Regla de oro:** `atomicworld/` nunca imprime ni pide datos. Las funciones
reciben valores y devuelven resultados. Para añadir una interfaz gráfica basta
con crear `ui/gui.py` que llame a `analyze()` o `match_particles()`, igual que
hace `cli.py`.

Los nombres de los elementos y las partículas en cada idioma son datos, así que están en el
núcleo (`atomicworld/names.py`) y los comparten la web, la consola y el visor. La búsqueda acepta
cualquier idioma, el símbolo o el número atómico, sin importar mayúsculas ni acentos:
`Hierro`, `iron`, `Ferro`, `Fe` y `26` dan el mismo elemento.

Los errores de las fórmulas (`FormulaError`) llevan, además del mensaje, un código y sus datos
(`error.code`, `error.params`), para que la web los escriba en cada idioma.

## Relative Developers

AtomicWorld es una app de [Relative Developers](https://relativedevelopers.com/atomicworld/).
`relativedevelopers.json` es su ficha (versión, estado, plataformas, icono y enlaces); la web de la
marca la lee con `python main.py --sync`.

## Novedades respecto al original

- Fórmulas químicas completas: `H2O`, `C6H12O6`, `Ca(OH)2`, `CH3COOH`... sin límite de elementos.
- Búsquedas por nombre o símbolo, sin distinguir mayúsculas; entradas erróneas ya no cierran el programa.
- Se calcula también el número de electrones.
- El tiempo por bit se mide de verdad (nanosegundos) en lugar de imprimir `time.time()`.
- "Back" vuelve al menú anterior en lugar de cerrar el programa.

## Conversor de masas

Viene de `StandardModelConversor.py` (en `legacy/`). En física de partículas las masas se dan
en energía (E = mc²); `atomicworld/units.py` las pasa a kilogramos:

    m [kg] = E [eV] · e / c²      con e = 1.602176634·10⁻¹⁹ J/eV y c = 299 792 458 m/s

Desde 2019 las dos constantes son exactas en el SI, así que 1 eV/c² = 1.78266192·10⁻³⁶ kg.
Además convierte a unidades de masa atómica (u, la unidad de la tabla periódica), compara
con la masa del electrón y del protón, y busca la partícula de masa más parecida.

```python
from atomicworld import units
units.convert(0.511, "MeV", "kg")        # 9.109e-31
units.Mass.of(12, "u").to("GeV")         # 11.18
```

Las masas de las partículas salen de `particles.json` (PDG 2024), no de la tabla del script
original, que tenía valores antiguos (Higgs 126 GeV, top 173.1 GeV, up 2.3 MeV...).
Los tests comparan los kilogramos con los valores medidos de CODATA 2022.

## Los tres primeros minutos

La simulación sigue al universo desde 10¹¹ K (0.01 s) hasta 10⁸ K (~3.5 h):

1. Neutrones y protones se transforman entre sí por interacciones débiles.
2. Hacia 1 s y 10¹⁰ K esas reacciones se "congelan": queda ~1 neutrón por cada 5–6 protones.
3. Los neutrones libres se desintegran mientras el universo se enfría.
4. Cuello de botella del deuterio: los fotones rompen el deuterio en cuanto se forma.
5. Hacia los 3–4 minutos (≈ 9·10⁸ K) el deuterio sobrevive y los neutrones acaban en helio-4.

**Modelo:** expansión de Friedmann con la aniquilación e⁺e⁻ tratada por conservación de
entropía; tasas débiles de Mukhanov (2004); desintegración del neutrón; mini red nuclear
n + p ⇄ D + γ (Saha) y D + D → ⁴He (efectiva). No calcula ³He ni ⁷Li.

| Magnitud | AtomicWorld | Referencia |
|---|---|---|
| Helio-4, Y_p | 0.245 | 0.247 (códigos completos), 0.245 ± 0.003 (observado) |
| D/H | 3.0·10⁻⁵ | 2.55·10⁻⁵ (observado) — el modelo solo da el orden de magnitud |
| ΔY por especie de neutrino | +0.013 | +0.013 |
| Tiempos de los fotogramas de Weinberg | ±10 % | *Los tres primeros minutos* |

Se pueden cambiar η (bariones por fotón), el número de especies de neutrinos y la vida
media del neutrón para ver cómo sería el helio en otros universos. El modo "partícula a
partícula" hace lo mismo con N nucleones que cambian al azar: con pocos, el resultado
fluctúa; con muchos, converge al 25 %.

## Datos y fuentes

Los datos se generan con `tools/build_data.py` (requiere `pip install mendeleev`,
solo para ese script; el programa no lo necesita).

| Dato | Fuente |
|---|---|
| Pesos atómicos, isótopos y abundancias | Base de datos `mendeleev` (IUPAC/CIAAW, NUBASE) |
| Semividas y modos de desintegración | NUBASE, vía `mendeleev` |
| Configuraciones electrónicas | `mendeleev` (estado fundamental, con excepciones como Cr, Cu y Pd) |
| Radios de van der Waals y colores | `mendeleev` (radios de Alvarez/Bondi; colores de Jmol) |
| Masas de quarks, leptones y bosones | Particle Data Group, *Review of Particle Physics* 2024 |
| Masa del neutrino electrónico (< 0.45 eV) | KATRIN, *Science* 2025 |
| Masas del protón y el neutrón | CODATA 2018 |
| Tasas débiles y criterio del deuterio | V. Mukhanov, *Nucleosynthesis without a computer* (2004) |
| n + p → D + γ | Ando et al., *Phys. Rev. C* 74 (2006) |
| Abundancias observadas de He y D | PDG 2024, revisión *Big-Bang Nucleosynthesis* |

Cada elemento guarda dos valores de neutrones:

- `neutrons`: los del isótopo más abundante (o del más estable si no hay isótopos naturales).
- `avg_neutrons`: la media ponderada por abundancia. Es la que se usa en los cálculos,
  porque una muestra real mezcla isótopos (el cloro tiene 18.48 neutrones de media).

Además, para el visor 3D: `electron_config` (`"[Ar] 3d6 4s2"`), `vdw_radius_pm` (el tamaño del
átomo) y `color`. Del 104 al 118 nadie ha medido el radio: se usa el del elemento de su grupo en el
periodo 6 (Z − 32) y se marca `vdw_estimated`.

### Isótopos

`isotopes.json` guarda los 3.557 isótopos de NUBASE con su masa, abundancia natural, semivida
(en segundos), modos de desintegración, espín y paridad. Se carga aparte (`IsotopeTable`)
porque solo hace falta al elegir un isótopo concreto:

```python
from atomicworld.repository import IsotopeTable
iso = IsotopeTable().get(6, 14)        # carbono-14
iso.half_life_s / 3.156e7              # ≈ 5700 años
iso.main_decay.mode                    # "B-" (β⁻)
```

En la fuente, las intensidades de los modos raros pierden el exponente (la fisión espontánea del
U-235 aparece como 7 % en lugar de 7·10⁻⁹ %). Por eso solo se guardan si todas suman ~100 %
(como en el K-40: 89 % β⁻ y 11 % β⁺); si no, solo la del modo principal. También se descartan los
modos permitidos pero nunca observados (la doble β⁺ del Ar-36).

### Correcciones respecto al original

- Añadido el Mercurio (faltaba y desplazaba todos los elementos del 80 en adelante).
- Renio: tenía los datos del Rutenio.
- Neutrones corregidos en ~30 elementos (se calculaban redondeando el peso atómico)
  y en los superpesados (Rf–Bh tenían todos 157).
- Masas de Seaborgio y Teneso (eran 0) y de otros superpesados.
- Puntos de fusión/ebullición de Be, C, P, Cl, Ni, Ga, Nb, Tm, Ir y Au.
- Masas de partículas actualizadas a PDG 2024, todas en MeV/c².
- Neutrinos: sus masas son cotas superiores, no valores medidos.
- Gravitón: marcado como hipotético (no es parte del Modelo Estándar) y con espín 2.
- Nombres IUPAC (Aluminium, Caesium) con alias para las grafías americanas.
