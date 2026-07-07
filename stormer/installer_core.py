"""Logique d'installation Stormer — dossiers, copie, raccourcis."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from stormer.config import APP_NAME, APP_VERSION

MARKER_NAME = "install_info.json"


def _branding_dir() -> Path:
    from stormer.branding import _assets_dir
    return _assets_dir()


def default_install_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Stormer"


def bundled_stormer_exe() -> Path:
    """Stormer.exe embarque (setup) ou dist/ en developpement."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "Stormer.exe"
        if candidate.is_file():
            return candidate
    same_dir = Path(sys.executable).resolve().parent / "Stormer.exe"
    if same_dir.is_file():
        return same_dir
    return Path(__file__).resolve().parent.parent / "dist" / "Stormer.exe"


def documents_stormer_dir() -> Path:
    return Path.home() / "Documents" / "Stormer"


def desktop_dir() -> Path:
    return Path.home() / "Desktop"


def start_menu_dir() -> Path:
    return (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
    )


def has_existing(install_dir: Path | None = None) -> bool:
    root = install_dir or default_install_dir()
    return (root / "Stormer.exe").is_file() or (root / MARKER_NAME).is_file()


def is_installed(install_dir: Path | None = None) -> bool:
    root = install_dir or default_install_dir()
    return (root / "Stormer.exe").is_file() and (root / MARKER_NAME).is_file()


def _stop_stormer_process() -> None:
    if sys.platform != "win32":
        return
    subprocess.run(
        ["taskkill", "/IM", "Stormer.exe", "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _remove_shortcuts() -> None:
    for link in (
        desktop_dir() / f"{APP_NAME}.lnk",
        start_menu_dir() / APP_NAME / f"{APP_NAME}.lnk",
        start_menu_dir() / f"{APP_NAME}.lnk",
    ):
        try:
            if link.is_file():
                link.unlink()
        except OSError:
            pass
    menu = start_menu_dir() / APP_NAME
    try:
        if menu.is_dir() and not any(menu.iterdir()):
            menu.rmdir()
    except OSError:
        pass


def uninstall(install_dir: Path) -> bool:
    """Desinstalle une version existante (exe, raccourcis, dossier)."""
    if not has_existing(install_dir):
        return False

    _stop_stormer_process()

    if install_dir.is_dir():
        for item in list(install_dir.iterdir()):
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except OSError:
                pass
        try:
            install_dir.rmdir()
        except OSError:
            pass

    _remove_shortcuts()
    return True


def create_shortcut(shortcut_path: Path, target: Path, working_dir: Path, description: str, icon: Path | None = None) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    ps_target = str(target).replace("'", "''")
    ps_work = str(working_dir).replace("'", "''")
    ps_link = str(shortcut_path).replace("'", "''")
    ps_desc = description.replace("'", "''")
    icon_line = ""
    if icon and icon.is_file():
        ps_icon = str(icon).replace("'", "''")
        icon_line = f"$l.IconLocation = '{ps_icon},0'; "
    script = (
        "$s = New-Object -ComObject WScript.Shell; "
        f"$l = $s.CreateShortcut('{ps_link}'); "
        f"$l.TargetPath = '{ps_target}'; "
        f"$l.WorkingDirectory = '{ps_work}'; "
        f"$l.Description = '{ps_desc}'; "
        f"{icon_line}"
        "$l.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def install(
    install_dir: Path,
    *,
    desktop_shortcut: bool = True,
    start_menu_shortcut: bool = True,
) -> Path:
    """Copie Stormer, cree l'arborescence et les raccourcis."""
    source = bundled_stormer_exe()
    if not source.is_file():
        raise FileNotFoundError(
            f"Stormer.exe introuvable.\nAttendu : {source}"
        )

    if has_existing(install_dir):
        uninstall(install_dir)

    install_dir.mkdir(parents=True, exist_ok=True)
    target_exe = install_dir / "Stormer.exe"
    shutil.copy2(source, target_exe)

    icon_src = _branding_dir() / "stormer.ico"
    icon_dst = install_dir / "stormer.ico"
    if icon_src.is_file():
        shutil.copy2(icon_src, icon_dst)
    shortcut_icon = icon_dst if icon_dst.is_file() else None

    docs = documents_stormer_dir()
    (docs / "exports").mkdir(parents=True, exist_ok=True)
    (docs / "sessions").mkdir(parents=True, exist_ok=True)
    (install_dir / "logs").mkdir(exist_ok=True)

    marker = install_dir / MARKER_NAME
    marker.write_text(
        f'{{"version":"{APP_VERSION}","app":"{APP_NAME}"}}\n',
        encoding="utf-8",
    )

    desc = f"{APP_NAME} — Acquisition capteurs Arduino"
    if desktop_shortcut:
        create_shortcut(desktop_dir() / f"{APP_NAME}.lnk", target_exe, install_dir, desc, shortcut_icon)
    if start_menu_shortcut:
        menu = start_menu_dir() / APP_NAME
        menu.mkdir(parents=True, exist_ok=True)
        create_shortcut(menu / f"{APP_NAME}.lnk", target_exe, install_dir, desc, shortcut_icon)

    return target_exe


def launch_app(install_dir: Path) -> None:
    exe = install_dir / "Stormer.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Application introuvable : {exe}")
    subprocess.Popen([str(exe)], cwd=str(install_dir))
