"""Interface graphique principale de Stormer."""

from __future__ import annotations

import io
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from stormer.ai_engine import MIN_POINTS, analyze_session
from stormer.charts import render_hourly_strip, render_sparkline
from stormer.config import APP_NAME, APP_VERSION, DEFAULT_BAUDRATE, MAX_TERMINAL_LINES
from stormer.data_parser import SessionData
from stormer.serial_manager import SerialManager
from stormer.sensors import (
    DISPLAY_ORDER,
    expected_keys,
    format_forecast,
    format_live,
    format_terminal_line,
    meta,
    value_hint,
)
from stormer.code_generator import export_dir, export_generated_files
from stormer.profile_info import boot_terminal_lines
from stormer.setup_config import HardwareProfile, load_profile
from stormer.branding import apply_window_icon, load_ctk_image
from stormer.setup_wizard import run_setup_wizard

# Couleurs
C_BG = "#0b0f14"
C_CARD = "#151b26"
C_CARD2 = "#1c2433"
C_ACCENT = "#3b82f6"
C_GREEN = "#22c55e"
C_CYAN = "#06b6d4"
C_ORANGE = "#f59e0b"
C_RED = "#ef4444"
C_MUTED = "#64748b"
C_TEXT = "#e2e8f0"

AI_DATA_HINT = (
    "Plus vous collectez de mesures, plus la prévision est fiable.\n"
    "Idéal : plusieurs minutes de données avant d'analyser."
)

AI_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class StormerApp(ctk.CTk):
    def __init__(self, profile: HardwareProfile | None = None):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=C_BG)
        self.title(f"{APP_NAME} v{APP_VERSION}")
        apply_window_icon(self)
        self.geometry("1200x760")
        self.minsize(960, 640)

        self._session = SessionData()
        self._message_queue: queue.Queue = queue.Queue()
        self._serial = SerialManager(self._on_serial_line, self._on_serial_error)
        self._port_var = tk.StringVar()
        self._status_var = tk.StringVar(value="● Hors ligne")
        self._stats_var = tk.StringVar(value="0 lignes · 0 points IA")
        self._live_cards: dict[str, dict] = {}
        self._cards_frame: ctk.CTkFrame | None = None
        self._connected = False
        self._ai_running = False
        self._ai_spinner_idx = 0
        self._pulse_on = False
        self._boot_idx = 0
        self._port_map: dict[str, str] = {}
        self._connecting = False
        self._images: list[ImageTk.PhotoImage] = []
        self._summary_labels: list[ctk.CTkLabel] = []
        self._chart_labels: list[ctk.CTkLabel] = []
        self._ai_card_widgets: list[ctk.CTkFrame] = []
        self._profile = profile or load_profile()
        self._unlocked = not self._profile.requires_rfid_unlock()
        self._app_logo: ctk.CTkImage | None = None
        self._boot_steps = boot_terminal_lines(self._profile)

        self._sync_exported_files()
        self._build_ui()
        self._setup_terminal_tags()
        self._refresh_ports()
        self.after(100, self._process_queue)
        self.after(300, self._boot_animation_step)
        self.after(500, self._pulse_indicator)

    def _setup_terminal_tags(self) -> None:
        tb = self._terminal._textbox
        tb.tag_configure("info", foreground=C_CYAN)
        tb.tag_configure("data", foreground=C_GREEN)
        tb.tag_configure("error", foreground=C_RED)
        tb.tag_configure("warn", foreground=C_ORANGE)
        tb.tag_configure("ai", foreground="#a78bfa")
        tb.tag_configure("muted", foreground=C_MUTED)
        tb.tag_configure("banner", foreground=C_ACCENT)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(4, 10))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_terminal_panel(body)
        self._build_side_panel(body)
        self._build_status_bar()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=96)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        title_row = ctk.CTkFrame(title_box, fg_color="transparent")
        title_row.pack(anchor="w")
        self._app_logo = load_ctk_image(36)
        if self._app_logo:
            ctk.CTkLabel(title_row, text="", image=self._app_logo).pack(side="left", padx=(0, 10))
        text_col = ctk.CTkFrame(title_row, fg_color="transparent")
        text_col.pack(side="left")
        ctk.CTkLabel(
            text_col, text="STORMER",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_col, text="Acquisition · Terminal · Prédiction IA",
            font=ctk.CTkFont(size=12), text_color=C_MUTED,
        ).pack(anchor="w")

        cards = ctk.CTkFrame(header, fg_color="transparent")
        cards.grid(row=0, column=1, padx=8, pady=8, sticky="e")
        self._cards_frame = cards
        self._rebuild_live_cards()

        self._conn_indicator = ctk.CTkLabel(
            header, text="●", font=ctk.CTkFont(size=26), text_color=C_RED,
        )
        self._conn_indicator.grid(row=0, column=2, padx=(4, 18), sticky="e")

    def _make_sensor_card(
        self, parent, title: str, var: tk.StringVar, unit: str, color: str
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, tk.StringVar]:
        card = ctk.CTkFrame(parent, fg_color=C_CARD2, corner_radius=12, width=185, height=82)
        card.pack_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=12), text_color=C_MUTED, anchor="w",
        ).grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")

        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.grid(row=1, column=0, padx=12, sticky="w")
        ctk.CTkLabel(
            val_row, textvariable=var,
            font=ctk.CTkFont(size=24, weight="bold"), text_color=color,
        ).pack(side="left")
        ctk.CTkLabel(
            val_row, text=unit, font=ctk.CTkFont(size=13), text_color=C_MUTED,
        ).pack(side="left", padx=(3, 0), pady=(8, 0))

        hint_var = tk.StringVar(value="")
        ctk.CTkLabel(
            card, textvariable=hint_var, font=ctk.CTkFont(size=10), text_color=C_MUTED, anchor="w",
        ).grid(row=2, column=0, padx=12, sticky="w")

        spark = ctk.CTkLabel(card, text="", width=150, height=22, fg_color="transparent")
        spark.grid(row=3, column=0, padx=10, pady=(0, 6), sticky="ew")
        return card, spark, hint_var

    def _rebuild_live_cards(self) -> None:
        if not self._cards_frame:
            return
        for w in self._cards_frame.winfo_children():
            w.destroy()
        self._live_cards.clear()
        for key in expected_keys(self._profile):
            self._ensure_live_card(key)

    def _ensure_live_card(self, key: str) -> None:
        if not self._cards_frame or key in self._live_cards:
            return
        info = meta(key)
        var = tk.StringVar(value="—")
        card, spark, hint_var = self._make_sensor_card(
            self._cards_frame, info["title"], var, info["unit"], info["color"]
        )
        card.pack(side="left", padx=5)
        self._live_cards[key] = {
            "var": var,
            "hint": hint_var,
            "spark": spark,
            "card": card,
            "history": [],
            "unit": info["unit"],
        }

    def _reset_live_card_values(self) -> None:
        for entry in self._live_cards.values():
            entry["var"].set("—")
            entry["hint"].set("")
            entry["history"].clear()
            entry["spark"].configure(image=None)

    def _build_terminal_panel(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=14)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            top, text="Terminal", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXT,
        ).pack(side="left")
        self._live_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=11), text_color=C_MUTED,
        )
        self._live_label.pack(side="right")

        self._terminal = ctk.CTkTextbox(
            panel,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#0a0e13",
            border_color="#2a3548",
            border_width=1,
            corner_radius=10,
            wrap="none",
        )
        self._terminal.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self._terminal.configure(state="disabled")

    def _build_side_panel(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        self._build_conn_card(panel)
        self._build_action_card(panel)

        report_wrap = ctk.CTkFrame(panel, fg_color=C_CARD, corner_radius=14)
        report_wrap.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        report_wrap.grid_rowconfigure(1, weight=1)
        report_wrap.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(report_wrap, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        ctk.CTkLabel(
            hdr, text="Previsions IA",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#029CFF",
        ).pack(side="left")
        self._ai_status_lbl = ctk.CTkLabel(
            hdr, text="—",
            font=ctk.CTkFont(size=10), text_color=C_MUTED,
        )
        self._ai_status_lbl.pack(side="right")

        self._ai_scroll = ctk.CTkScrollableFrame(
            report_wrap, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=C_CARD2, scrollbar_button_hover_color=C_MUTED,
        )
        self._ai_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self._render_ai_placeholder()

    def _build_conn_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=14)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Connexion série", font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 8), sticky="w")

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14)
        row1.grid_columnconfigure(0, weight=1)
        self._port_menu = ctk.CTkOptionMenu(
            row1, variable=self._port_var, values=["Aucun port"], height=36, width=260,
        )
        self._port_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(row1, text="↻", width=42, height=36, command=self._refresh_ports).grid(
            row=0, column=1
        )

        ctk.CTkLabel(
            card,
            text="Fermez le moniteur série Arduino IDE avant de connecter.",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED,
            wraplength=280,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, padx=14, pady=(0, 4), sticky="w")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 14))
        row2.grid_columnconfigure((0, 1), weight=1)

        self._connect_btn = ctk.CTkButton(
            row2, text="Connecter", height=38, fg_color=C_ACCENT,
            hover_color="#2563eb", command=self._toggle_connection,
        )
        self._connect_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            row2, text="Auto-détecter", height=38,
            fg_color=C_CARD2, hover_color="#263044", command=self._auto_detect,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _build_action_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=14)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Session", font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(12, 8), sticky="w")

        ctk.CTkButton(
            card, text="💾  Enregistrer en .txt", height=38,
            command=self._save_session,
        ).grid(row=1, column=0, padx=14, pady=4, sticky="ew")

        self._ai_btn = ctk.CTkButton(
            card, text="Analyser avec l'IA", height=40,
            fg_color="#16a34a", hover_color="#15803d", command=self._run_analysis,
        )
        ctk.CTkButton(
            card, text="🗑  Effacer la session", height=34,
            fg_color="#7f1d1d", hover_color="#991b1b", command=self._clear_session,
        ).grid(row=3, column=0, padx=14, pady=(4, 4), sticky="ew")
        self._ai_btn.grid(row=2, column=0, padx=14, pady=4, sticky="ew")

        tools = ctk.CTkFrame(card, fg_color="transparent")
        tools.grid(row=4, column=0, sticky="ew", padx=14, pady=(4, 4))
        tools.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            tools, text="Guides", height=28,
            fg_color=C_CARD2, hover_color="#263044", command=self._open_docs_folder,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkButton(
            tools, text="Exporter", height=28,
            fg_color=C_CARD2, hover_color="#263044", command=self._export_profile_files,
        ).grid(row=0, column=1, sticky="ew", padx=3)
        ctk.CTkButton(
            tools, text="Materiel", height=28,
            fg_color=C_CARD2, hover_color="#263044", command=self._open_setup_wizard,
        ).grid(row=0, column=2, sticky="ew", padx=(3, 0))
        ctk.CTkLabel(card, text="", height=6).grid(row=5, column=0)

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=34)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            bar, textvariable=self._status_var, font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).grid(row=0, column=0, padx=16, sticky="w")
        self._lock_var = tk.StringVar(value=self._lock_label())
        self._lock_lbl = ctk.CTkLabel(
            bar, textvariable=self._lock_var, font=ctk.CTkFont(size=11),
            text_color=C_GREEN if self._unlocked else C_ORANGE,
        )
        self._lock_lbl.grid(row=0, column=1, padx=16, sticky="e")
        ctk.CTkLabel(
            bar, textvariable=self._stats_var, font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).grid(row=0, column=2, padx=16, sticky="e")

    # ── Animations ───────────────────────────────────────────

    def _boot_animation_step(self) -> None:
        if self._boot_idx < len(self._boot_steps):
            line = self._boot_steps[self._boot_idx]
            if self._boot_idx == 0:
                tag = "banner"
            elif line.startswith("[BOOT]   "):
                tag = "data"
            else:
                tag = "info"
            self._append_terminal(line + "\n", tag=tag)
            self._boot_idx += 1
            self.after(320, self._boot_animation_step)
        else:
            self._append_terminal("─" * 44 + "\n", tag="muted")

    def _sync_exported_files(self) -> None:
        if not self._profile.setup_complete:
            return
        try:
            export_generated_files(self._profile)
        except OSError:
            pass

    def _open_docs_folder(self) -> None:
        import os
        import subprocess
        import sys

        folder = export_dir()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except OSError:
            messagebox.showwarning("Dossier", f"Impossible d'ouvrir :\n{folder}")

    def _export_profile_files(self) -> None:
        try:
            paths = export_generated_files(self._profile)
            self._open_docs_folder()
            names = "\n".join(f"· {p.name}" for p in paths)
            messagebox.showinfo(
                "Export OK",
                f"Fichiers mis a jour dans Documents\\Stormer :\n\n{names}",
            )
            self._append_terminal("[INFO] Export Arduino + guides mis a jour.\n", tag="info")
        except OSError as exc:
            messagebox.showerror("Export", str(exc))

    def _pulse_indicator(self) -> None:
        if self._connected:
            color = C_GREEN if self._pulse_on else "#166534"
            self._conn_indicator.configure(text_color=color)
            self._pulse_on = not self._pulse_on
        else:
            self._conn_indicator.configure(text_color=C_RED)
        self.after(600, self._pulse_indicator)

    def _ai_spinner_tick(self) -> None:
        if not self._ai_running:
            self._live_label.configure(text="")
            return
        ch = AI_SPINNER[self._ai_spinner_idx % len(AI_SPINNER)]
        self._ai_spinner_idx += 1
        self._live_label.configure(text=f"{ch} Analyse IA en cours...")
        self.after(80, self._ai_spinner_tick)

    # ── Serial ───────────────────────────────────────────────

    def _on_serial_line(self, line: str) -> None:
        self._message_queue.put(("line", line))

    def _on_serial_error(self, error: str) -> None:
        self._message_queue.put(("error", error))

    def _process_queue(self) -> None:
        try:
            while True:
                msg_type, data = self._message_queue.get_nowait()
                if msg_type == "line":
                    self._handle_incoming_line(data)
                elif msg_type == "error":
                    self._handle_serial_error(data)
                elif msg_type == "ai_done":
                    self._finish_analysis(data)
                elif msg_type == "ai_err":
                    self._fail_analysis(data)
                elif msg_type == "connect_ok":
                    self._finish_connect(data)
                elif msg_type == "connect_err":
                    self._fail_connect(data)
        except queue.Empty:
            pass
        self.after(50, self._process_queue)

    def _lock_label(self) -> str:
        if not self._profile.requires_rfid_unlock():
            return ""
        return "🔓 Deverrouille" if self._unlocked else "🔒 Verrouille — presentez la puce RFID"

    def _set_unlocked(self, unlocked: bool) -> None:
        if not self._profile.requires_rfid_unlock():
            return
        if self._unlocked == unlocked:
            return
        self._unlocked = unlocked
        self._lock_var.set(self._lock_label())
        self._lock_lbl.configure(text_color=C_GREEN if unlocked else C_ORANGE)
        tag = "data" if unlocked else "warn"
        msg = "Systeme debloque (puce RFID OK)" if unlocked else "Systeme verrouille — puce RFID requise"
        self._append_terminal(f"[INFO] {msg}\n", tag=tag)

    def _handle_incoming_line(self, line: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        point = self._session.add_line(line)

        if point and "unlock" in point.values:
            self._set_unlocked(point.values["unlock"] >= 1.0)

        if line.strip().startswith("#") or "ERREUR" in line.upper():
            tag = "error" if "ERREUR" in line.upper() else "muted"
            self._append_terminal(f"[{ts}] {line}\n", tag=tag)
        elif point:
            vals = format_terminal_line(point.values)
            self._append_terminal(f"[{ts}] {vals}\n", tag="data")
            self._update_live_cards(point.values)
        else:
            self._append_terminal(f"[{ts}] {line}\n", tag="info")

        self._update_stats()

    def _handle_serial_error(self, error: str) -> None:
        self._append_terminal(f"\n[ERREUR] {error}\n", tag="error")
        self._set_connected(False)
        self._connect_btn.configure(state="normal", text="Connecter")
        self._serial.disconnect()

    def _update_live_cards(self, values: dict[str, float]) -> None:
        for key, value in values.items():
            if key == "unlock":
                continue
            self._ensure_live_card(key)
            entry = self._live_cards.get(key)
            if not entry:
                continue
            info = meta(key)
            entry["var"].set(format_live(key, value))
            hint = value_hint(key, value)
            if key == "air":
                entry["hint"].set("0 = charge · 1023 = pur" + (f" · {hint}" if hint else ""))
            elif key == "soil":
                entry["hint"].set("humidite du sol en %" + (f" · {hint}" if hint else ""))
            else:
                entry["hint"].set(hint)
            entry["history"].append(value)
            if len(entry["history"]) > 40:
                entry["history"].pop(0)
            self._update_sparkline(entry["spark"], entry["history"], info["color"])

    def _update_sparkline(self, label: ctk.CTkLabel, history: list[float], color: str) -> None:
        if len(history) < 2:
            return
        png = render_sparkline(history, color)
        if not png:
            return
        img = Image.open(io.BytesIO(png))
        photo = ImageTk.PhotoImage(img)
        self._images.append(photo)
        if len(self._images) > 20:
            self._images = self._images[-20:]
        label.configure(image=photo)
        label.image = photo

    def _render_ai_placeholder(self) -> None:
        self._clear_ai_scroll()
        ctk.CTkLabel(
            self._ai_scroll,
            text="Prévisions horaires (cycle jour/nuit + tendance)\naprès analyse des données capteur.",
            font=ctk.CTkFont(size=11), text_color=C_MUTED, justify="center",
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            self._ai_scroll,
            text=AI_DATA_HINT,
            font=ctk.CTkFont(size=10), text_color=C_ORANGE, wraplength=260, justify="center",
        ).pack(pady=(0, 20))

    def _ai_data_notice(self, point_count: int) -> str:
        if point_count < 10:
            return "Peu de mesures — prévision approximative. Laissez tourner plus longtemps."
        if point_count < 30:
            return "Prévision correcte. Encore 1–2 min de données amélioreront le calcul."
        return "Bonne base de données pour une prévision fiable."

    def _clear_ai_scroll(self) -> None:
        for w in self._ai_scroll.winfo_children():
            w.destroy()
        self._chart_labels.clear()
        self._ai_card_widgets.clear()

    def _build_weather_widget(self, sensor, accent: str) -> None:
        """Widget compact : valeur actuelle + prévisions horaires."""
        box = ctk.CTkFrame(self._ai_scroll, fg_color=C_CARD2, corner_radius=10)
        box.pack(fill="x", padx=2, pady=(0, 8))
        self._ai_card_widgets.append(box)

        # Ligne actuelle
        top = ctk.CTkFrame(box, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            top, text=sensor.display_name,
            font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).pack(side="left")
        trend_txt = {"croissante": "hausse", "decroissante": "baisse", "stable": "stable"}[sensor.trend]
        conf_color = C_GREEN if sensor.confidence_pct >= 70 else C_ORANGE if sensor.confidence_pct >= 50 else C_MUTED
        ctk.CTkLabel(
            top, text=f"{sensor.trend_icon} {trend_txt} · fiabilite {sensor.confidence_pct}%",
            font=ctk.CTkFont(size=10), text_color=conf_color,
        ).pack(side="right")

        display_val = format_live(sensor.name, sensor.current)
        if sensor.unit:
            display_val = f"{display_val}{sensor.unit}"
        ctk.CTkLabel(
            box, text=display_val,
            font=ctk.CTkFont(size=32, weight="bold"), text_color=accent,
        ).pack(anchor="w", padx=12, pady=(0, 6))

        # Slots horaires (style app meteo)
        row = ctk.CTkFrame(box, fg_color="#0d1117", corner_radius=8)
        row.pack(fill="x", padx=10, pady=(0, 8))
        for slot in sensor.hourly:
            cell = ctk.CTkFrame(row, fg_color="transparent", width=42)
            cell.pack(side="left", expand=True, fill="x", padx=1, pady=6)
            ctk.CTkLabel(
                cell, text=slot.hour_label,
                font=ctk.CTkFont(size=9), text_color=C_MUTED,
            ).pack()
            ctk.CTkLabel(
                cell, text=format_forecast(sensor.name, slot.value, sensor.unit),
                font=ctk.CTkFont(size=12, weight="bold"), text_color=accent,
            ).pack()

        # Mini bandeau graphique discret
        if sensor.hourly:
            labels = [h.hour_label for h in sensor.hourly]
            vals = [h.value for h in sensor.hourly]
            png = render_hourly_strip(vals, labels, color=accent, width=4.2, height=0.85)
            if png:
                img = Image.open(io.BytesIO(png))
                photo = ImageTk.PhotoImage(img)
                self._images.append(photo)
                lbl = ctk.CTkLabel(box, text="", image=photo)
                lbl.image = photo
                lbl.pack(padx=8, pady=(0, 10))
                self._chart_labels.append(lbl)

    def _render_ai_panel(self, result) -> None:
        self._clear_ai_scroll()
        if not result.ok or not result.sensors:
            self._ai_status_lbl.configure(text="—", text_color=C_MUTED)
            ctk.CTkLabel(
                self._ai_scroll, text=result.summary,
                font=ctk.CTkFont(size=11), text_color=C_ORANGE, wraplength=260,
            ).pack(pady=16)
            return

        self._ai_status_lbl.configure(text=result.summary, text_color=C_MUTED)

        def sort_key(s) -> int:
            name = s.name.lower()
            return DISPLAY_ORDER.index(name) if name in DISPLAY_ORDER else 99

        for sensor in sorted(result.sensors, key=sort_key):
            accent = meta(sensor.name)["color"]
            self._build_weather_widget(sensor, accent)

        for alert in result.alerts[:3]:
            ctk.CTkLabel(
                self._ai_scroll, text=alert,
                font=ctk.CTkFont(size=10), text_color=C_ORANGE, wraplength=260,
            ).pack(pady=(0, 4))

        notice = self._ai_data_notice(len(self._session.points))
        notice_color = C_GREEN if len(self._session.points) >= 30 else C_ORANGE if len(self._session.points) < 10 else C_MUTED
        ctk.CTkLabel(
            self._ai_scroll, text=notice,
            font=ctk.CTkFont(size=10), text_color=notice_color, wraplength=270, justify="left",
        ).pack(padx=4, pady=(2, 8))

    def _open_setup_wizard(self) -> None:
        if self._serial.is_connected:
            messagebox.showinfo("Configuration", "Deconnectez l'Arduino avant de reconfigurer.")
            return
        profile = run_setup_wizard(force=False, parent=self, initial=self._profile)
        if profile:
            self._profile = profile
            self._unlocked = not profile.requires_rfid_unlock()
            self._lock_var.set(self._lock_label())
            self._lock_lbl.configure(
                text_color=C_GREEN if self._unlocked else C_ORANGE,
            )
            self._boot_steps = boot_terminal_lines(profile)
            self._sync_exported_files()
            self._rebuild_live_cards()
            extra = ""
            if profile.requires_rfid_unlock():
                extra = f" | Puce RFID : {profile.rfid_uid}"
            self._append_terminal(
                f"[INFO] Materiel : {profile.board_label()} | "
                f"{', '.join(profile.sensor_labels())}{extra}\n",
                tag="info",
            )

    # ── Actions ──────────────────────────────────────────────

    def _refresh_ports(self) -> None:
        ports = self._serial.list_ports()
        self._port_map.clear()

        if not ports:
            self._port_menu.configure(values=["Aucun port detecte"])
            self._port_var.set("Aucun port detecte")
            self._append_terminal("[INFO] Aucun port COM detecte — branchez l'Arduino.\n", tag="warn")
            return

        labels = []
        for p in ports:
            self._port_map[p.label] = p.device
            labels.append(p.label)

        self._port_menu.configure(values=labels)

        current = self._port_var.get()
        if current in self._port_map:
            return

        best = next((p for p in ports if p.is_arduino), ports[0])
        self._port_var.set(best.label)

    def _auto_detect(self) -> None:
        self._refresh_ports()
        port = self._serial.find_arduino_port()
        if not port:
            messagebox.showwarning("Auto-detection", "Aucun port serie detecte.\nBranchez l'Arduino en USB.")
            return
        for label, device in self._port_map.items():
            if device == port:
                self._port_var.set(label)
                break
        self._append_terminal(f"[INFO] Port selectionne : {port}\n", tag="info")

    def _get_selected_port(self) -> str | None:
        val = self._port_var.get()
        if val.startswith("Aucun port"):
            return None
        device = self._port_map.get(val)
        if device:
            return device
        # Secours : extraire COMx au debut du libelle
        if "|" in val:
            return val.split("|")[0].strip()
        return val.strip() or None

    def _set_connected(self, on: bool, port: str = "") -> None:
        self._connected = on
        if on:
            self._status_var.set(f"● Connecté · {port} · {DEFAULT_BAUDRATE} bauds")
        else:
            self._status_var.set("● Hors ligne")

    def _toggle_connection(self) -> None:
        if self._serial.is_connected:
            self._serial.disconnect()
            self._connect_btn.configure(state="normal", text="Connecter")
            self._set_connected(False)
            self._append_terminal("[INFO] Deconnecte.\n", tag="info")
            return

        if self._connecting:
            return

        self._refresh_ports()
        port = self._get_selected_port()
        if not port:
            messagebox.showwarning("Connexion", "Aucun port COM disponible.\nBranchez l'Arduino puis cliquez ↻")
            return

        self._connecting = True
        self._connect_btn.configure(state="disabled", text="Connexion...")
        self._append_terminal(f"[INFO] Connexion a {port}...\n", tag="info")

        def worker() -> None:
            try:
                self._serial.connect(port, DEFAULT_BAUDRATE)
                self._message_queue.put(("connect_ok", port))
            except ConnectionError as exc:
                self._message_queue.put(("connect_err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_connect(self, port: str) -> None:
        self._connecting = False
        self._connect_btn.configure(state="normal", text="Deconnecter")
        self._set_connected(True, port)
        self._append_terminal(f"[INFO] Connecte a {port} @ {DEFAULT_BAUDRATE} bauds\n", tag="data")
        self._append_terminal("[INFO] Reception des donnees...\n", tag="muted")

    def _fail_connect(self, error: str) -> None:
        self._connecting = False
        self._connect_btn.configure(state="normal", text="Connecter")
        self._set_connected(False)
        self._append_terminal(f"\n[ERREUR] Connexion echouee\n{error}\n", tag="error")
        messagebox.showerror("Connexion impossible", error)

    def _save_session(self) -> None:
        if not self._session.raw_lines:
            messagebox.showinfo("Enregistrement", "Aucune donnée à enregistrer.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texte", "*.txt"), ("Tous", "*.*")],
            initialfile=f"stormer_{datetime.now():%Y%m%d_%H%M%S}.txt",
        )
        if not path:
            return
        self._session.export_txt(path)
        self._append_terminal(f"[INFO] Session → {path}\n", tag="info")
        messagebox.showinfo("OK", f"Sauvegardé:\n{path}")

    def _run_analysis(self) -> None:
        if self._ai_running:
            return
        if self._profile.requires_rfid_unlock() and not self._unlocked:
            messagebox.showwarning(
                "Verrouille",
                "Presentez la puce RFID autorisee sur le lecteur\n"
                "pour debloquer l'analyse IA.",
            )
            return
        n = len(self._session.points)
        if n < MIN_POINTS:
            messagebox.showwarning(
                "IA",
                f"Pas assez de données ({n}/{MIN_POINTS} mesures).\n\n"
                f"{AI_DATA_HINT}",
            )
            return

        self._ai_running = True
        self._ai_btn.configure(state="disabled", text="Analyse...")
        self._append_terminal("\n[IA] Lancement de l'analyse...\n", tag="ai")
        self._ai_spinner_tick()

        def worker() -> None:
            try:
                result = analyze_session(self._session)
                self._message_queue.put(("ai_done", (result, None)))
            except Exception as exc:
                self._message_queue.put(("ai_err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_analysis(self, payload) -> None:
        result, _report = payload
        self._ai_running = False
        self._ai_btn.configure(state="normal", text="Analyser avec l'IA")
        self._render_ai_panel(result)
        tag = "ai" if result.ok else "warn"
        msg = "[IA] Previsions horaires mises a jour\n" if result.ok else "[IA] Donnees insuffisantes\n"
        self._append_terminal(msg, tag=tag)

    def _fail_analysis(self, error: str) -> None:
        self._ai_running = False
        self._ai_btn.configure(state="normal", text="Analyser avec l'IA")
        self._append_terminal(f"[IA] ERREUR: {error}\n", tag="error")
        messagebox.showerror("Erreur IA", error)

    def _clear_session(self) -> None:
        if not self._session.raw_lines:
            return
        if messagebox.askyesno("Effacer", "Effacer toute la session ?"):
            self._session.clear()
            self._reset_live_card_values()
            self._ai_status_lbl.configure(text="—", text_color=C_MUTED)
            self._render_ai_placeholder()
            self._update_stats()
            self._append_terminal("[INFO] Session effacée.\n", tag="warn")

    # ── UI helpers ───────────────────────────────────────────

    def _append_terminal(self, text: str, tag: str = "") -> None:
        self._terminal.configure(state="normal")
        tb = self._terminal._textbox
        if tag:
            tb.insert("end", text, tag)
        else:
            tb.insert("end", text)
        n = int(tb.index("end-1c").split(".")[0])
        if n > MAX_TERMINAL_LINES:
            tb.delete("1.0", f"{n - MAX_TERMINAL_LINES}.0")
        tb.see("end")
        self._terminal.configure(state="disabled")

    def _update_stats(self) -> None:
        n_raw = len(self._session.raw_lines)
        n_pts = len(self._session.points)
        self._stats_var.set(f"{n_raw} lignes · {n_pts}/{MIN_POINTS} pts IA")

    def on_closing(self) -> None:
        self._serial.disconnect()
        self.destroy()


def main(profile: HardwareProfile | None = None) -> None:
    app = StormerApp(profile)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
