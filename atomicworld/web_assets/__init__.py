"""Archivos de la interfaz de los visores 3D en el navegador, comunes a las webs de AtomicWorld y
DNAinvent: así hay un solo archivo de cada y no copias que se separan.

    v3d-ui.js / v3d-ui.css   teclas dibujadas, botones, ayuda (H) y «Saber más» (L)
    v3d-plastic.js           modo plástico 3D (bolas de plástico con WebGL 2)
    img/plastic/             sus imágenes: protón, neutrón, electrón, quarks u y d, gluón

Cada web los sirve tal cual en /static/v3d/:

    from atomicworld.web_assets import ASSETS_DIR
    app.mount("/static/v3d", StaticFiles(directory=ASSETS_DIR), name="v3d")   # antes que /static
"""
from pathlib import Path

ASSETS_DIR = Path(__file__).parent
FILES = ("v3d-ui.js", "v3d-ui.css", "v3d-plastic.js",
         *(f"img/plastic/{name}.webp" for name in ("proton", "neutron", "electron", "up", "down", "gluon")))
