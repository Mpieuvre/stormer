"""Chemins application — compatibles mode developpement et .exe PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Racine du projet (dev) ou dossier contenant Stormer.exe."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    """Config materiel — a cote de l'exe ou a la racine du projet."""
    return app_root() / "stormer_config.json"
