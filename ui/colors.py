"""Colores ANSI para la consola.

En el original cada partícula guardaba su nombre ya coloreado ('Color_name',
'Color_binary'). Ahora el color depende de la familia y se aplica solo al
mostrar: los datos quedan limpios y una GUI puede usar sus propios colores.
"""
try:
    import colorama
    colorama.just_fix_windows_console()
except (ImportError, AttributeError):
    pass  # sin colorama los códigos ANSI siguen funcionando en Linux/macOS

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BG_RED = "\033[101m"
BG_GREEN = "\033[102m"
BG_BLUE = "\033[104m"

FAMILY_COLORS = {
    "Quark": GREEN,
    "Antiquark": BLUE,
    "Lepton": MAGENTA,
    "Antilepton": CYAN,
    "Gauge Boson": BG_RED,
    "Scalar Boson": BG_GREEN,
    "Hypothetical": YELLOW,
}


def paint(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def paint_family(text: str, family: str) -> str:
    return paint(text, FAMILY_COLORS.get(family, ""))


def rainbow_title(text: str) -> str:
    """Título multicolor como el 'Subatomic World' del original."""
    palette = [GREEN, BLUE, MAGENTA, CYAN, BG_BLUE, BG_RED]
    words = text.split(" ")
    return " ".join(paint(w, palette[i % len(palette)]) for i, w in enumerate(words))
