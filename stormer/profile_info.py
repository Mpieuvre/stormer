"""Profil materiel — textes pour l'UI, le boot et le terminal."""

from __future__ import annotations

from stormer.setup_config import HardwareProfile


def profile_lines(profile: HardwareProfile) -> list[str]:
    """Lignes resume du profil actif."""
    lines = [
        f"Carte      : {profile.board_label()}",
        f"Capteurs   : {', '.join(profile.sensor_labels()) or '—'}",
        f"Ecran      : {profile.display_label()}",
        f"RFID       : {profile.access_label()}",
        f"LED        : {profile.output_label()}",
        f"Sans fil   : {profile.wireless_label()}",
    ]
    if profile.requires_rfid_unlock():
        lines.append(f"Puce RFID  : {profile.rfid_uid}")
    return lines


def boot_terminal_lines(profile: HardwareProfile) -> list[str]:
    """Messages boot affiches dans le terminal de l'app."""
    lines = [
        "[BOOT] Demarrage Stormer...",
        "[BOOT] Chargement profil materiel...",
    ]
    for row in profile_lines(profile):
        lines.append(f"[BOOT]   {row}")
    lines += [
        "[BOOT] Capteurs actifs transmis a l'interface",
        "[BOOT] Moteur IA pret (scikit-learn)",
        "[BOOT] Guides : Documents\\Stormer\\BRANCHEMENT.txt",
        "[BOOT] Libs Arduino : Documents\\Stormer\\DEPENDANCES.txt",
        "[BOOT] Pret — branchez l'Arduino et connectez",
    ]
    return lines


def sidebar_hardware_text(profile: HardwareProfile) -> str:
    """Texte compact pour le panneau Materiel."""
    parts = [
        profile.board_label(),
        ", ".join(s.split("—")[0].strip() for s in profile.sensor_labels()[:3]),
    ]
    if len(profile.sensors) > 3:
        parts[-1] += f" +{len(profile.sensors) - 3}"
    txt = "\n".join(profile_lines(profile))
    return txt
