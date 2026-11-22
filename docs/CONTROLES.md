# Controles de los visores 3D

Estándar común de los cuatro visores 3D de Relative Developers, en la consola (escritorio) y en
la web:

| Visor | App | Escritorio | Web |
|---|---|---|---|
| Átomo en 3D | AtomicWorld | `viewer/` | `viewer3d.js` |
| Microscopio 3D | DNAinvent | `microscope/` | `microscope3d.js` |
| Proteína 3D | DNAinvent | el Microscopio 3D con una proteína | `microscope3d.js` (`kind: "protein"`) |
| Cuerpo humano | DNAinvent | `bodyviewer/` | `anatomy.js` |

**Regla: una tecla = una sola acción en los cuatro visores.** Si un visor no tiene esa función, la
tecla no hace otra cosa en él: el visor avisa de que no está disponible ahí.

La tabla de verdad es `atomicworld/web_assets/controls.json`. La leen `atomicworld/controls.py`
(visores de escritorio, con pyglet) y `atomicworld/web_assets/v3d-controls.js` (las dos webs, que
lo sirven en `/static/v3d/`). Un test (`tests/test_controls.py`) comprueba que ninguna tecla se
repite y que la copia de la web es idéntica.

## Común a los cuatro

| Acción | Teclas | Ratón | Táctil (web) |
|---|---|---|---|
| Acercarse / alejarse | W / S | rueda | pellizcar |
| Izquierda / derecha | A / D | arrastrar con el botón derecho, o Mayús + arrastrar | arrastrar con dos dedos |
| Subir / bajar | Espacio / C | (igual) | (igual) |
| Girar | Q / E | | |
| Mirar (mover la cámara) | ← ↑ ↓ → | arrastrar con el botón izquierdo | arrastrar con un dedo |
| Más rápido | Mayús (mantenida) | | |
| Ir a lo que tienes delante o elegido | Enter · Mayús+Enter = hasta el final | doble clic | doble toque |
| Subir un nivel | Retroceso | | botón |
| Vista inicial | R | | botón |
| Modo de vista | M · Mayús+M = al revés | | botón |
| Fondo claro u oscuro | B | | botón |
| Saber más | L | | botón |
| Ayuda | H | | botón |
| Pantalla completa | F (y F11 en el escritorio) | | botón |
| Salir | Esc | | |

**Al arrastrar, lo que arrastras sigue al dedo o al ratón**, como en Google Earth. Por ejemplo,
deslizas dos dedos hacia arriba y la vista sube. Las flechas, en cambio, mueven la cámara: → mira
a la derecha.

Esc cierra la ventana de ayuda; si no está abierta, suelta lo elegido (Cuerpo humano) o para el
piloto automático; si no hay nada de eso, cierra la ventana del visor (en el escritorio).

El fondo claro y la ayuda se recuerdan: en la web, en el navegador (`relativedevelopers.v3d.light`);
en el escritorio, en los ajustes de cada programa.

### Cómo se entiende cada acción en cada visor

| Acción | Átomo / Microscopio / Proteína (cámara de **nave**) | Cuerpo humano (cámara de **órbita**) |
|---|---|---|
| W / S, rueda, pellizcar | avanzar o retroceder (más despacio cuanto más cerca) | acercar o alejar el zoom |
| Q / E | girar sobre ti mismo | girar alrededor del cuerpo |
| ← ↑ ↓ →, arrastrar | girar la cabeza | girar alrededor de lo que miras |
| Enter, doble clic | bajar al siguiente nivel (átomo → núcleo → nucleón → quarks) | centrar la pieza elegida |
| Retroceso | subir al nivel anterior | subir a la parte que contiene la elegida (de la válvula al corazón) |
| M | didáctico · realista · (atómico) · plástico 3D | colores por sistema o de un solo color |
| L | la ficha «Saber más» de lo que tienes delante | la ficha de la pieza elegida |
| Clic o toque | | elegir una pieza |

## Teclas reservadas para funciones propias

| Tecla | Función | Dónde |
|---|---|---|
| O | subnivel siguiente | Átomo, Microscopio y Proteína (en el nivel atómico) |
| I | orbital siguiente | Átomo, Microscopio y Proteína (en el nivel atómico) |
| N / P | elemento siguiente o anterior | Átomo |
| [ / ] | isótopo anterior o siguiente | Átomo |
| U | unir o separar las dos proteínas | Proteína 3D al comparar |
| V | ver la otra proteína | Proteína 3D al comparar |
| X | aislar lo elegido | Cuerpo humano |
| T | todas las capas | Cuerpo humano |

Libres para el futuro: G, J, K, Y, Z y los números.

## Botones (web)

Cuadrícula de 3 columnas (`V3DControls.buttons`), en este orden:

1. **Moverse:** Bajar · Subir · Hasta el final (Cuerpo humano: Centrar · Subir a la parte · Aislar)
2. **Cómo se ve:** Modo (Colores) · Fondo claro · Vista inicial
3. **Lo propio de cada visor:** Subnivel · Orbital (Átomo, Microscopio, Proteína); Unir o separar ·
   Ver la otra (solo al comparar); Todas las capas (Cuerpo humano)
4. **Siempre la última:** Saber más · Ayuda · Pantalla completa

En el móvil (menos de 520 px de ancho) se ocultan las teclas y el texto pasa a otra línea.

## Fondo claro en los visores de nave

Las partículas brillan con mezcla aditiva sobre negro, que no funciona sobre blanco. Por eso, con el
fondo claro se invierte la imagen y se gira el tono 180° (en la web, `filter: invert(1)
hue-rotate(180deg)`; en el escritorio, un último paso de dibujo con la misma matriz): el negro pasa
a blanco y cada color conserva su tono. Lo que no debe invertirse (las bolas del modo plástico) se
dibuja ya invertido; como esta transformación es su propia inversa, al invertir la imagen vuelve a
su color exacto. Cuerpo humano dibuja su fondo claro directamente.

## Para añadir una función nueva

1. Elige una tecla libre (ver arriba) y añádela a `controls.json`: en `press` (o en `held` si se
   mantiene), en `viewers` del visor que la tenga y, si lleva botón, en `buttons`.
2. Copia `controls.json` entero en el bloque `STANDARD` de `v3d-controls.js`.
3. Escribe sus textos (`web.v3d.*` en las webs; la ayuda de cada visor de escritorio).
4. Pasa los tests de los cuatro repositorios.
