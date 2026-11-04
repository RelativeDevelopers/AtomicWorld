"""La consola de principio a fin, en los tres idiomas, con entradas simuladas.

Recorre todos los menús y comprueba que no se cuela ninguna clave sin traducir
("console.xxx") ni ningún error.
"""
import re

import pytest

from ui import cli, launcher, settings

# Un recorrido por todas las opciones (la primera línea responde a "¿qué idioma?")
SESSION = [
    "1",                                   # 1: Periodic table
    "1", "H2O", "18", "Ca(OH", "Xx2", "", # calculadora: bien, paréntesis sin cerrar, símbolo desconocido
    "2", "Oro", "999", "",                 # visor 3D: isótopo que no existe, luego el de por defecto
    "2", "Zz",                             # elemento desconocido
    "0",
    "2",                                   # Standard Model
    "2", "Electrón",
    "3", "1", "2", "0,511", "parsec", "MeV", "", "0",
    "1", "40", "1", "2", "3", "4", "9", "0",
    "0",
    "3",                                   # Los tres primeros minutos
    "1", "2", "", "", "", "3", "500", "4", "0",
    "9",                                   # opción no válida
    "4", "3",                              # cambiar el idioma a catalán
    "0",
]
LANG_CHOICE = {"en": "1", "es": "2", "ca": "3"}
EXPECTED = {"en": "Until next time.", "es": "Hasta la próxima.", "ca": "Fins a la propera."}


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "SETTINGS_FILE", tmp_path / "settings.json")
    opened = []
    monkeypatch.setattr(launcher, "open_viewer", lambda el, iso, lang=None: opened.append((el.symbol, iso.a, lang)))
    monkeypatch.setattr(launcher, "missing_dependencies", lambda: "")
    return opened


def play(monkeypatch, answers):
    queue = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": print(prompt, end="") or next(queue))
    cli.run()


@pytest.mark.parametrize("lang", ["en", "es", "ca"])
def test_whole_console_in_every_language(lang, isolated, monkeypatch, capsys):
    play(monkeypatch, [LANG_CHOICE[lang]] + SESSION)
    out = capsys.readouterr().out
    leftovers = re.findall(r"\b(?:console|errors|events|units|viewer)\.[a-z_.]+", out)
    assert not leftovers, leftovers
    assert isolated == [("Au", 197, lang)]                    # el visor se abre en el idioma elegido
    assert EXPECTED["ca"] in out                              # al final se cambió a catalán
    assert settings.language() == "ca"


def test_language_is_asked_only_the_first_time(isolated, monkeypatch, capsys):
    play(monkeypatch, ["2", "0"])
    play(monkeypatch, ["0"])                                  # segunda vez: no pregunta
    out = capsys.readouterr().out
    assert out.count("Language · Idioma · Idioma") == 1
    assert out.count(EXPECTED["es"]) == 2


def test_spanish_numbers_and_errors(isolated, monkeypatch, capsys):
    play(monkeypatch, ["2", "1", "1", "Xx2", "H2O", "18,015", "", "0", "0"])
    out = capsys.readouterr().out
    assert "No existe ningún elemento con el símbolo Xx" in out
    assert "18,015 g" in out and "6,0221 × 10^23" in out      # coma decimal


def test_periodic_table_lists_names_in_the_chosen_language(isolated, monkeypatch, capsys):
    play(monkeypatch, ["3", "1", "0", "0"])
    out = capsys.readouterr().out
    assert "Hidrogen" in out and "Oganessó" in out and "Taula periòdica" in out
