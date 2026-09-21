"""Rutas de recursos empaquetados y de datos persistentes de la aplicación."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parent


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def app_data_dir() -> Path:
    """Datos editables fuera del bundle; en desarrollo se mantiene el repositorio."""
    if not is_frozen():
        return BUNDLE_DIR
    root = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    target = root / 'Universidad de Cantabria' / 'Prensa Marshall USB-4716'
    target.mkdir(parents=True, exist_ok=True)
    return target


def config_file() -> Path:
    target = app_data_dir() / 'config.json'
    source = BUNDLE_DIR / 'config.json'
    if is_frozen() and not target.exists() and source.exists():
        shutil.copyfile(source, target)
    return target


def output_dir(configured: str = 'ensayos') -> Path:
    path = Path(configured)
    if not path.is_absolute():
        path = app_data_dir() / path
    path.mkdir(parents=True, exist_ok=True)
    return path
