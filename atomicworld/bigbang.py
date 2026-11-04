"""Juego clásico del programa original: 'Big Bang' de bits.

(La simulación física del Big Bang está en nucleosynthesis.py.)

'Big Bang' de bits: genera bits aleatorios, los agrupa en bytes y busca
qué bytes coinciden con el código binario de alguna partícula.

Todas las funciones son puras (entran datos, salen datos), así que la misma
lógica sirve para la consola y para una futura interfaz gráfica.
"""
import random
import time
from dataclasses import dataclass

from .constants import BITS_PER_BYTE
from .models import Particle
from .repository import ParticleCatalog


def generate_bits(n: int, rng: random.Random | None = None) -> str:
    """Genera una cadena de n bits aleatorios ('0101...')."""
    if n <= 0:
        raise ValueError("The number of bits must be greater than 0.")
    rng = rng or random.Random()
    return "".join(rng.choice("01") for _ in range(n))


def generate_bits_timed(n: int, rng: random.Random | None = None) -> tuple[str, list[int]]:
    """Como generate_bits, pero mide cuánto tarda cada bit (en nanosegundos).

    En el original se imprimía time.time() (segundos desde 1970), que no medía nada.
    """
    if n <= 0:
        raise ValueError("The number of bits must be greater than 0.")
    rng = rng or random.Random()
    bits, durations = [], []
    for _ in range(n):
        start = time.perf_counter_ns()
        bits.append(rng.choice("01"))
        durations.append(time.perf_counter_ns() - start)
    return "".join(bits), durations


# --- Transformaciones -------------------------------------------------------

def invert(bits: str) -> str:
    """Cambia ceros por unos y viceversa."""
    return bits.translate(str.maketrans("01", "10"))


def reverse(bits: str) -> str:
    """Invierte el orden de la cadena."""
    return bits[::-1]


def invert_and_reverse(bits: str) -> str:
    return invert(reverse(bits))


TRANSFORMS = {
    "invert": ("Swap zeros for ones, and vice versa", invert),
    "reverse": ("Reverse the bit string", reverse),
    "invert_reverse": ("Swap zeros for ones and reverse the bit string", invert_and_reverse),
}


# --- Bytes y coincidencias --------------------------------------------------

def split_bytes(bits: str) -> list[str]:
    """Agrupa los bits de 8 en 8. El último grupo puede quedar incompleto."""
    return [bits[i:i + BITS_PER_BYTE] for i in range(0, len(bits), BITS_PER_BYTE)]


@dataclass(frozen=True)
class ByteMatch:
    byte: str
    particle: Particle | None   # None si el byte no coincide con ninguna partícula

    @property
    def is_complete(self) -> bool:
        return len(self.byte) == BITS_PER_BYTE


@dataclass(frozen=True)
class BigBangResult:
    bits: str
    matches: list[ByteMatch]

    @property
    def full_bytes(self) -> int:
        return len(self.bits) // BITS_PER_BYTE

    @property
    def leftover_bits(self) -> int:
        return len(self.bits) % BITS_PER_BYTE

    @property
    def found(self) -> list[Particle]:
        return [m.particle for m in self.matches if m.particle is not None]


def match_particles(bits: str, catalog: ParticleCatalog) -> BigBangResult:
    """Compara cada byte con los códigos de las partículas.

    Cada byte se procesa UNA sola vez (el original usaba str.replace() sobre toda
    la cadena, que volvía a colorear bytes repetidos).
    """
    matches = [
        ByteMatch(byte, catalog.by_binary(byte) if len(byte) == BITS_PER_BYTE else None)
        for byte in split_bytes(bits)
    ]
    return BigBangResult(bits, matches)
