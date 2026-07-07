"""Gestion de la communication série avec Arduino."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable

import serial
import serial.tools.list_ports

from stormer.config import ARDUINO_VID_PIDS, DEFAULT_BAUDRATE, SERIAL_TIMEOUT

_ARDUINO_KEYWORDS = ("arduino", "ch340", "ch341", "cp210", "usb-serial", "usb serial")


@dataclass
class PortInfo:
    device: str
    description: str
    is_arduino: bool
    label: str


def normalize_com_port(port: str) -> str:
    """Format Windows pour COM10+ : \\\\.\\COM10"""
    port = port.strip().upper()
    m = re.match(r"^COM(\d+)$", port)
    if m and int(m.group(1)) > 9:
        return rf"\\.\{port}"
    return port


def format_connection_error(port: str, exc: Exception) -> str:
    msg = str(exc).lower()
    if isinstance(exc, PermissionError) or "permission" in msg or "accès refusé" in msg or "access is denied" in msg:
        return (
            f"Impossible d'ouvrir {port} — port déjà utilisé.\n\n"
            "Fermez imperativement :\n"
            "  - Moniteur serie Arduino IDE\n"
            "  - Autre fenetre Stormer ouverte\n"
            "  - Putty / Tera Term / autre logiciel serie\n\n"
            "Puis reessayez."
        )
    if "fileno" in msg or "not found" in msg or "introuvable" in msg:
        return (
            f"Le port {port} n'existe plus.\n\n"
            "Débranchez/rebranchez l'Arduino puis cliquez ↻ pour actualiser."
        )
    return f"Impossible de se connecter à {port}.\n\nDétail : {exc}"


def _clean_port_name(device: str) -> str:
    d = device.upper().strip()
    prefix = "\\\\.\\"
    if d.startswith(prefix):
        return d[len(prefix):]
    return d


class SerialManager:
    def __init__(self, on_line: Callable[[str], None], on_error: Callable[[str], None]):
        self._on_line = on_line
        self._on_error = on_error
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    @staticmethod
    def _is_arduino_port(port) -> bool:
        desc = (port.description or "").lower()
        if port.vid and port.pid and (port.vid, port.pid) in ARDUINO_VID_PIDS:
            return True
        return any(kw in desc for kw in _ARDUINO_KEYWORDS)

    @staticmethod
    def list_ports() -> list[PortInfo]:
        ports: list[PortInfo] = []
        for port in serial.tools.list_ports.comports():
            desc = (port.description or "Port série").strip()
            is_arduino = SerialManager._is_arduino_port(port)
            short = desc.split("(")[0].strip() or desc
            tag = "Arduino" if is_arduino else short
            label = f"{port.device}  |  {tag}"
            ports.append(
                PortInfo(
                    device=port.device,
                    description=desc,
                    is_arduino=is_arduino,
                    label=label,
                )
            )

        ports.sort(key=lambda p: (not p.is_arduino, p.device))
        return ports

    @staticmethod
    def find_arduino_port() -> str | None:
        ports = SerialManager.list_ports()
        for p in ports:
            if p.is_arduino:
                return p.device
        # Éviter COM1 fantôme si d'autres ports existent
        for p in ports:
            if p.device.upper() != "COM1":
                return p.device
        return ports[0].device if ports else None

    @staticmethod
    def port_exists(device: str) -> bool:
        clean = _clean_port_name(device)
        return any(p.device.upper() == clean for p in serial.tools.list_ports.comports())

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._serial is not None and self._serial.is_open

    def connect(self, port: str, baudrate: int = DEFAULT_BAUDRATE) -> None:
        self.disconnect()
        port = normalize_com_port(port)

        if not self.port_exists(port):
            raise ConnectionError(format_connection_error(port, OSError("Port introuvable")))

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=SERIAL_TIMEOUT,
                write_timeout=1,
                dsrdtr=False,
                rtscts=False,
            )
            time.sleep(1.8)  # Reset Arduino après ouverture du port
            self._serial.reset_input_buffer()
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
        except (serial.SerialException, OSError, PermissionError) as exc:
            self._serial = None
            raise ConnectionError(format_connection_error(port, exc)) from exc

    def disconnect(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except serial.SerialException:
                    pass
            self._serial = None
        self._thread = None

    def _read_loop(self) -> None:
        while self._running:
            try:
                with self._lock:
                    ser = self._serial
                if not ser or not ser.is_open:
                    break
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self._on_line(line)
            except serial.SerialException as exc:
                port_name = "?"
                with self._lock:
                    if self._serial:
                        port_name = self._serial.port
                self._on_error(format_connection_error(port_name, exc))
                break
            except Exception as exc:
                self._on_error(f"Erreur de lecture : {exc}")
