"""Los archivos de los visores web que comparten AtomicWorld_web y DNAinvent_web."""
import tomllib
from fnmatch import fnmatch
from pathlib import Path

from atomicworld.web_assets import ASSETS_DIR, FILES


def test_every_file_is_there():
    assert all((ASSETS_DIR / name).is_file() for name in FILES)


def test_every_file_goes_into_the_package():
    # Si no está en package-data, pip no lo instala y la web de Render no lo encuentra
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = pyproject["tool"]["setuptools"]["package-data"]["atomicworld"]
    assert all(any(fnmatch(f"web_assets/{name}", p) for p in patterns) for name in FILES)


def test_plastic_images_are_looked_up_where_the_webs_serve_them():
    assert 'base = "/static/v3d/img/plastic/"' in (ASSETS_DIR / "v3d-plastic.js").read_text(encoding="utf-8")
