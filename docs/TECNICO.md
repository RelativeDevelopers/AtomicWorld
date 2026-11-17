# AtomicWorld · Documentación técnica

Cómo funciona AtomicWorld por dentro: la física del visor 3D, la estructura del código, los modelos
y las fuentes de los datos. La presentación del programa y cómo instalarlo están en el
[README](../README.md).

## Física del visor 3D

En el modo plástico los electrones dan vueltas como en el modelo de Bohr y los quarks tienen
tamaño, para poder verlos: es un modelo de juguete, y el HUD lo explica. Las imágenes de las
bolas están en `viewer/render/textures/`; se dibujan con la profundidad de una esfera de
verdad, así que las que se solapan en el núcleo se cortan bien.

**Física:** orbitales hidrogenoides con la carga efectiva de Slater ([`atomicworld/atoms.py`](../atomicworld/atoms.py)),
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
│   ├── web_assets/          Interfaz común de los visores web (v3d-ui.js/.css, v3d-plastic.js e
│   │                        imágenes): la sirven las webs de AtomicWorld y DNAinvent en /static/v3d/
│   ├── scene/               Física de los visores 3D (necesita NumPy: pip install atomicworld[scene])
│   │   ├── orbitals.py      Nubes de electrones, orbitales reales p/d/f, regla de Hund
│   │   ├── nucleus.py       Empaquetado de nucleones, Woods–Saxon
│   │   └── describe.py      Resumen de un átomo para el visor web (/api/atom de atomicworld_web)
│   ├── chemistry.py         Fórmula → moles → átomos → quarks
│   ├── units.py             Conversor de masas: eV/c², u, g y kg
│   ├── bigbang.py           Juego de bits, transformaciones y coincidencias
│   ├── nucleosynthesis.py   Los tres primeros minutos: n/p, D, ³He, ⁴He y ⁷Li
│   ├── nuclear_rates.py     Las 18 reacciones nucleares de la red, con su fuente
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

La simulación sigue al universo desde 2·10¹¹ K (0,002 s) hasta 10⁸ K (~3,5 h):

1. Neutrones y protones se transforman entre sí por interacciones débiles.
2. Hacia 1 s y 10¹⁰ K esas reacciones se "congelan": queda ~1 neutrón por cada 5–6 protones.
3. Los neutrones libres se desintegran mientras el universo se enfría.
4. Cuello de botella del deuterio: los fotones rompen el deuterio en cuanto se forma.
5. Hacia los 3–4 minutos (≈ 9·10⁸ K) el deuterio sobrevive y los neutrones acaban en helio-4.
   Quedan restos de deuterio, helio-3 (y tritio) y litio-7 (y berilio-7).

**Modelo** (`atomicworld/nucleosynthesis.py` y `atomicworld/nuclear_rates.py`):

- **Expansión:** Friedmann con fotones, e± y N_ν especies de neutrinos. La aniquilación e⁺e⁻ se
  trata con conservación de entropía, así que T_ν/T = (4/11)^⅓ sale sola. La densidad de
  bariones sigue a la entropía: η es la proporción de hoy, y antes de la aniquilación había
  menos fotones por barión.
- **Tasas débiles n ⇄ p:** integrales de Born completas de las seis reacciones (n + ν ⇄ p + e⁻,
  n + e⁺ ⇄ p + ν̄, n ⇄ p + e⁻ + ν̄), con las distribuciones de Fermi-Dirac de e± y neutrinos,
  normalizadas con la vida media medida (Weinberg 1972; Bernstein, Brown y Feinberg 1989). Se
  calculan una vez en una rejilla de temperaturas y se interpolan.
- **Red nuclear:** 8 núcleos (n, p, D, T, ³He, ⁴He, ⁷Li, ⁷Be) y 18 reacciones, las de la tabla
  de abajo. Las reacciones inversas (por ejemplo D + γ → n + p) salen por balance detallado,
  con los coeficientes de Wagoner (1969) y Kawano (1992); un test comprueba el de p(n,γ)D con
  los espines y las masas.
- **Integración:** BDF2 de paso variable, implícito y resuelto con Newton, porque las
  reacciones con fotones son hasta 10¹⁵ veces más rápidas que el paso. 2.500 pasos en
  progresión geométrica; cuatro quintas partes, por debajo de 0,5 MeV. Doblar los pasos
  cambia los resultados menos de un 0,1 %.
- **Correcciones a las tasas débiles:** Born no incluye las correcciones radiativas (con la de
  Coulomb) ni la masa finita de los nucleones. Según PRIMAT suben Y_p en 44·10⁻⁴, un 1,8 %
  (Pitrou et al., *Phys. Rep.* 754, 1, 2018; tabla 2 de arXiv:1909.12046). Se aplican al Y_p
  final (`helium_fraction`); el de la red sin corregir está en `helium_fraction_born`, y la curva
  del gráfico es la de la red.

| Magnitud | AtomicWorld | Códigos completos¹ | AlterBBN 2.2² | Observado³ |
|---|---|---|---|---|
| Y_p (helio-4, fracción de masa) | 0,2468 | 0,2469 ± 0,0002 | 0,2452 | 0,245 ± 0,003 |
| Y_p con Born, sin correcciones | 0,2424 | 0,2427⁴ | — | — |
| D/H (×10⁻⁵) | 2,42 | 2,57 ± 0,13 | 2,33 | 2,508 ± 0,029 |
| ³He/H (×10⁻⁵) | 1,02 | 1,00 ± 0,09 | 1,02 | no se puede medir |
| ⁷Li/H (×10⁻¹⁰) | 5,37 | 4,72 ± 0,72 | 5,69 | 1,45 ± 0,25 |
| ΔY_p por especie de neutrino | +0,013 | +0,013 | +0,013 | — |
| Tiempos de los fotogramas de Weinberg | ±10 % | — | — | *Los tres primeros minutos* |

¹ Fields, Olive, Yeh y Young, *JCAP* 03, 010 (2020), con el η de Planck (y PRIMAT para Y_p:
0,24709). ² Con los mismos parámetros que AtomicWorld (η = 6,1·10⁻¹⁰, 3 neutrinos, τ = 878,4 s).
³ PDG 2026, revisión *Big-Bang Nucleosynthesis* (B. Fields, P. Molaro y S. Sarkar, agosto de
2025). ⁴ PRIMAT menos sus correcciones (0,24709 − 0,0044).

Las diferencias entre los códigos completos vienen sobre todo de las tasas medidas de las
reacciones del deuterio y del ³He(α,γ)⁷Be, que cada grupo evalúa a su manera. La del litio no
se arregla con ninguna de ellas: es el **problema del litio**, la teoría da unas 3 veces más
litio del que se ve en las estrellas más viejas de la Galaxia.

**El tritio y el berilio-7** siguen vivos al terminar la simulación (semividas de 12 años y de
53 días). Se cuentan como ³He y ⁷Li, que es en lo que acaban, igual que en los códigos completos.

Se pueden cambiar η (bariones por fotón), el número de especies de neutrinos y la vida
media del neutrón para ver cómo sería el universo en otros casos. El modo "partícula a
partícula" hace lo mismo con N nucleones que cambian al azar: con pocos, el resultado
fluctúa; con muchos, converge al 25 %.

### Las reacciones de la red

| Reacción | Fuente de la tasa |
|---|---|
| p(n,γ)D | Ando et al., *Phys. Rev. C* 74, 025809 (2006) |
| D(p,γ)³He, D(d,n)³He, D(d,p)T | Coc et al., *Phys. Rev. D* 92, 123526 (2015), tablas |
| ³He(n,p)T, ⁷Be(n,p)⁷Li, ⁷Li(p,α)⁴He, T(α,γ)⁷Li, T(d,n)⁴He, ³He(d,p)⁴He, ⁷Li(d,nα)⁴He | Serpico et al., *JCAP* 12, 010 (2004) |
| ³He(α,γ)⁷Be | Cyburt y Davids, *Phys. Rev. C* 78, 064614 (2008) |
| ⁷Be(n,α)⁴He | Hou et al., *Phys. Rev. C* 91, 055802 (2015) |
| ³He(³He,2p)⁴He | NACRE, Angulo et al., *Nucl. Phys. A* 656, 3 (1999) |
| T(p,γ)⁴He, ⁷Be(d,pα)⁴He | Caughlan y Fowler, *At. Data Nucl. Data Tables* 40, 283 (1988) |
| D(n,γ)T, ³He(n,γ)⁴He | Wagoner, *ApJS* 18, 247 (1969) |

Las fórmulas se pasaron a Python desde AlterBBN 2.2 (Arbey et al., arXiv:1806.11095), que
reúne las mismas fuentes; se compararon con las originales en C y coinciden hasta la última
cifra. En la tabla de D(d,p)T, la copia de AlterBBN tiene una errata en T9 = 1,5 (2,882·10⁷,
entre 1,565·10⁷ y 2,181·10⁷): aquí va 1,882·10⁷. Los tests comparan los resultados con AlterBBN
para tres valores de η.

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
| Masas del protón y el neutrón | CODATA 2022 |
| Tasas débiles n ⇄ p | Aproximación de Born (Weinberg 1972; Bernstein, Brown y Feinberg, *Rev. Mod. Phys.* 61, 25, 1989) |
| Correcciones a las tasas débiles | Pitrou et al., *Phys. Rep.* 754, 1 (2018) |
| Reacciones nucleares de la nucleosíntesis | Ver [Las reacciones de la red](#las-reacciones-de-la-red) |
| Abundancias observadas de He, D y Li | PDG 2026, revisión *Big-Bang Nucleosynthesis* (agosto de 2025) |
| Abundancias predichas por los códigos completos | Fields et al., *JCAP* 03, 010 (2020) |

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
