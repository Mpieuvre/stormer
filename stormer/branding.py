"""Logo et icones Stormer — dev et .exe."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "assets"
        if bundled.is_dir():
            return bundled
    root = Path(__file__).resolve().parent.parent / "assets"
    return root


def logo_png() -> Path:
    return _assets_dir() / "stormer_logo.png"


def logo_small_png() -> Path:
    return _assets_dir() / "stormer_logo_sm.png"


def installer_banner_png() -> Path:
    return _assets_dir() / "installer_banner.png"


def icon_ico() -> Path:
    return _assets_dir() / "stormer.ico"


def license_txt() -> Path:
    return _assets_dir() / "LICENSE.txt"


def load_ctk_image(size: int = 48) -> ctk.CTkImage | None:
    path = logo_small_png() if size <= 96 else logo_png()
    if not path.is_file():
        return None
    img = Image.open(path).convert("RGBA")
    return ctk.CTkImage(
        light_image=img,
        dark_image=img,
        size=(size, size),
    )


def apply_window_icon(window) -> None:
    ico = icon_ico()
    if ico.is_file():
        try:
            window.iconbitmap(str(ico))
        except Exception:
            pass
