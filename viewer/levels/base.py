"""
Interfaz común de todos los niveles de profundidad.

Cada nivel trabaja en su propia unidad (pm, fm, 0,1 fm) para que los números siempre
estén en un rango cómodo. Al entrar en un "hijo", el motor convierte la posición de la
nave a las coordenadas locales del hijo:

    pos_hijo = (pos_padre - child.center) * child.scale

Los textos se piden al traductor (self.tr) en el momento de mostrarlos: así la tecla L
cambia el idioma al instante, sin reconstruir nada.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np


@dataclass
class Child:
    key: object                      # identificador estable (para cachear)
    center: np.ndarray               # en unidades del padre
    scale: float                     # unidades del hijo por unidad del padre
    create: Callable[[], "Level"]    # construye el nivel interior


@dataclass
class Focus:
    """Lo que la nave tiene delante, para el HUD."""
    title: str
    detail: str = ""
    explanation: list = field(default_factory=list)   # solo modo didáctico
    distance: Optional[float] = None                   # unidades locales


class Level:
    depth = 0             # 0 = átomo, 1 = núcleo, 2 = nucleón
    unit_m = 1.0
    # modo de visualización (engine.MODES). Lo pone el motor antes de build(); el argumento
    # didactic de build/render/focus sigue diciendo si los textos son didácticos.
    mode = "didactic"          # metros por unidad local

    def __init__(self, tr):
        self.tr = tr

    @property
    def name(self) -> str:
        raise NotImplementedError

    def build(self, renderer, didactic: bool):
        raise NotImplementedError

    def set_mode(self, renderer, didactic: bool):
        self.release()
        self.build(renderer, didactic)

    def update(self, dt: float, time: float):
        """Animación propia del nivel (opcional)."""

    def render(self, renderer, cam, didactic: bool, fade: float):
        raise NotImplementedError

    def surface_distance(self, pos: np.ndarray) -> float:
        """Distancia (unidades locales) al objeto más cercano: fija la velocidad de la nave."""
        raise NotImplementedError

    def child_to_enter(self, pos: np.ndarray) -> Optional[Child]:
        return None

    def should_exit(self, pos: np.ndarray) -> bool:
        return False

    def focus(self, pos: np.ndarray, forward: np.ndarray, didactic: bool) -> Optional[Focus]:
        return None

    def time_info(self) -> str:
        return ""

    # --- autopiloto ------------------------------------------------------------------
    def view_distance(self) -> float:
        """Distancia al centro desde la que se ve bien el nivel entero (al subir)."""
        raise NotImplementedError

    def dive_target(self, pos: np.ndarray, forward: np.ndarray):
        """(punto al que volar para bajar de nivel, texto del destino), o None si no hay hijo."""
        return None

    def release(self):
        pass
