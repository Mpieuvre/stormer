"""Assistant de configuration materiel — interface Stormer."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from stormer.branding import apply_window_icon, load_ctk_image
from stormer.code_generator import (
    EXPORT_FILES,
    export_dir,
    export_file_content,
    export_generated_files,
    generate_dependencies,
    generate_sketch,
    generate_wiring,
)
from stormer.setup_config import (
    ACCESS,
    BOARDS,
    DISPLAYS,
    OUTPUTS,
    SENSORS,
    WIRELESS,
    HardwareProfile,
    load_profile,
    save_profile,
)

C_BG = "#0b0f14"
C_CARD = "#151b26"
C_CARD2 = "#1c2433"
C_ACCENT = "#029CFF"
C_ACCENT_DIM = "#1E2025"
C_GREEN = "#22c55e"
C_TEXT = "#e2e8f0"
C_MUTED = "#64748b"

STEP_TITLES = ("Carte Arduino", "Capteurs", "Peripheriques", "Code & export")


class SetupWizard:
    """Configuration materiel — fenetre standalone ou modale."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        force: bool = False,
        initial: HardwareProfile | None = None,
    ):
        self.master = master
        self.result: HardwareProfile | None = None
        self._force = force
        self._step = 0
        self._steps_total = 4
        self._step_dots: list[tuple[ctk.CTkFrame, ctk.CTkLabel]] = []

        base = initial or load_profile()
        self._board_var = tk.StringVar(value=base.board)
        self._sensor_vars = {k: tk.BooleanVar(value=(k in base.sensors)) for k in SENSORS}
        self._display_var = tk.StringVar(value=base.display)
        self._wireless_var = tk.StringVar(value=base.wireless)
        self._access_var = tk.StringVar(value=base.access)
        self._output_var = tk.StringVar(value=base.output)
        self._rfid_uid = base.rfid_uid

        master.configure(fg_color=C_BG)
        master.title("Stormer — Configuration materiel")
        apply_window_icon(master)
        master.geometry("740x900")
        master.resizable(False, False)
        master.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_shell()
        self._show_step(0)

    def _build_shell(self) -> None:
        m = self.master
        m.grid_columnconfigure(0, weight=1)
        m.grid_rowconfigure(2, weight=1)

        outer = ctk.CTkFrame(m, fg_color=C_ACCENT_DIM, corner_radius=0)
        outer.grid(row=0, column=0, sticky="ew")
        outer.grid_columnconfigure(0, weight=1)

        accent = ctk.CTkFrame(outer, fg_color=C_ACCENT, height=3, corner_radius=0)
        accent.grid(row=0, column=0, sticky="ew")

        header = ctk.CTkFrame(outer, fg_color=C_CARD, corner_radius=0)
        header.grid(row=1, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        logo_row = ctk.CTkFrame(header, fg_color="transparent")
        logo_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=22, pady=(18, 8))
        logo = load_ctk_image(40)
        if logo:
            ctk.CTkLabel(logo_row, text="", image=logo).pack(side="left", padx=(0, 12))
        col = ctk.CTkFrame(logo_row, fg_color="transparent")
        col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            col, text="Configuration materielle",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=C_ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            col,
            text="Choisissez votre carte, capteurs et peripheriques — Stormer genere le code.",
            font=ctk.CTkFont(size=12), text_color=C_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        dots_row = ctk.CTkFrame(header, fg_color="transparent")
        dots_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=22, pady=(8, 18))
        for i, title in enumerate(STEP_TITLES):
            pill = ctk.CTkFrame(dots_row, fg_color=C_CARD2, corner_radius=20)
            pill.pack(side="left", padx=(0, 8))
            dot = ctk.CTkLabel(
                pill, text=f"  {i + 1}. {title}  ",
                font=ctk.CTkFont(size=11),
                text_color=C_MUTED,
            )
            dot.pack(padx=4, pady=4)
            self._step_dots.append((pill, dot))

        ctk.CTkFrame(m, fg_color="#1c2433", height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew",
        )

        self._body = ctk.CTkFrame(m, fg_color="transparent")
        self._body.grid(row=2, column=0, sticky="nsew", padx=22, pady=(14, 10))
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

        footer = ctk.CTkFrame(m, fg_color=C_CARD, corner_radius=0, height=64)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        self._back_btn = ctk.CTkButton(
            footer, text="Retour", width=110, height=36,
            fg_color=C_CARD2, hover_color="#263044", command=self._prev_step,
        )
        self._back_btn.grid(row=0, column=0, padx=18, pady=14)

        self._step_lbl = ctk.CTkLabel(footer, text="Etape 1 / 4", text_color=C_MUTED)
        self._step_lbl.grid(row=0, column=1)

        self._next_btn = ctk.CTkButton(
            footer, text="Suivant", width=130, height=36,
            fg_color=C_ACCENT, hover_color="#0284d4", command=self._next_step,
        )
        self._next_btn.grid(row=0, column=2, padx=18, pady=14)

    def _step_header(self, parent, title: str, subtitle: str) -> None:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            box, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            box, text=subtitle, font=ctk.CTkFont(size=12), text_color=C_MUTED,
        ).pack(anchor="w", pady=(4, 0))

    def _make_scroll(self, parent, height: int = 480) -> ctk.CTkScrollableFrame:
        return ctk.CTkScrollableFrame(
            parent,
            height=height,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_fg_color=C_BG,
            scrollbar_button_color=C_BG,
            scrollbar_button_hover_color=C_CARD2,
        )

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        box = ctk.CTkFrame(parent, fg_color=C_CARD2, corner_radius=12)
        box.pack(fill="x", pady=(0, 10))
        bar = ctk.CTkFrame(box, fg_color=C_ACCENT, width=4, corner_radius=0)
        bar.pack(side="left", fill="y", padx=(0, 0), pady=0)
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", expand=True, padx=14, pady=12)
        ctk.CTkLabel(
            inner, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w", pady=(0, 8))
        return inner

    def _clear_body(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()

    def _show_step(self, n: int) -> None:
        self._step = n
        self._step_lbl.configure(text=f"Etape {n + 1} / {self._steps_total}")
        self._back_btn.configure(state="normal" if n > 0 else "disabled")
        self._next_btn.configure(text="Terminer" if n == 3 else "Suivant")
        for i, (pill, dot) in enumerate(self._step_dots):
            if i == n:
                pill.configure(fg_color="#0d2840", border_width=1, border_color=C_ACCENT)
                dot.configure(text_color=C_ACCENT, font=ctk.CTkFont(size=11, weight="bold"))
            elif i < n:
                pill.configure(fg_color=C_CARD2, border_width=0)
                dot.configure(text_color=C_GREEN, font=ctk.CTkFont(size=11))
            else:
                pill.configure(fg_color=C_CARD2, border_width=0)
                dot.configure(text_color=C_MUTED, font=ctk.CTkFont(size=11))
        self._clear_body()
        [self._step_board, self._step_sensors, self._step_extras, self._step_finish][n]()

    def _step_board(self) -> None:
        wrap = ctk.CTkFrame(self._body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        self._step_header(wrap, "Quelle carte Arduino utilisez-vous ?", "Branchez-la en USB avant de continuer.")
        sf = self._make_scroll(wrap, height=520)
        sf.pack(fill="both", expand=True)
        grid = ctk.CTkFrame(sf, fg_color="transparent")
        grid.pack(fill="x")
        for i, (key, label) in enumerate(BOARDS.items()):
            row = ctk.CTkFrame(grid, fg_color=C_CARD, corner_radius=10)
            row.pack(fill="x", pady=4)
            ctk.CTkRadioButton(
                row, text=label, variable=self._board_var, value=key,
                font=ctk.CTkFont(size=13), radiobutton_width=20, radiobutton_height=20,
            ).pack(anchor="w", padx=14, pady=12)

    def _step_sensors(self) -> None:
        wrap = ctk.CTkFrame(self._body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        self._step_header(wrap, "Quels capteurs avez-vous ?", "Cochez tout ce qui est branche sur votre montage.")

        card = ctk.CTkFrame(wrap, fg_color=C_CARD2, corner_radius=12)
        card.pack(fill="both", expand=True, pady=(0, 8))
        cols = ctk.CTkFrame(card, fg_color="transparent")
        cols.pack(fill="x", padx=16, pady=16)
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        items = list(SENSORS.items())
        mid = (len(items) + 1) // 2
        for col, chunk in zip((left, right), (items[:mid], items[mid:])):
            for key, label in chunk:
                ctk.CTkCheckBox(
                    col, text=label, variable=self._sensor_vars[key],
                    font=ctk.CTkFont(size=12), checkbox_width=22, checkbox_height=22,
                ).pack(anchor="w", pady=5, padx=2)
        ctk.CTkLabel(
            wrap, text="DHT11 + DHT22 : seul le DHT22 sera utilise dans le code.",
            font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).pack(anchor="w")

    def _step_extras(self) -> None:
        wrap = ctk.CTkFrame(self._body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        self._step_header(wrap, "Ecran, securite & peripheriques", "RFID, LED et communication sans fil.")
        sf = self._make_scroll(wrap, height=500)
        sf.pack(fill="both", expand=True)

        disp = self._section(sf, "Ecran")
        for key, label in DISPLAYS.items():
            ctk.CTkRadioButton(disp, text=label, variable=self._display_var, value=key).pack(anchor="w", pady=4)

        acc = self._section(sf, "Puce RFID")
        for key, label in ACCESS.items():
            ctk.CTkRadioButton(acc, text=label, variable=self._access_var, value=key).pack(anchor="w", pady=4)
        ctk.CTkLabel(
            acc, text="Puce autorisee generee automatiquement dans le code.",
            font=ctk.CTkFont(size=10), text_color=C_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        out = self._section(sf, "LED indicatrices")
        for key, label in OUTPUTS.items():
            ctk.CTkRadioButton(out, text=label, variable=self._output_var, value=key).pack(anchor="w", pady=4)
        ctk.CTkLabel(
            out, text="Vert = OK · Orange = mesure · Rouge = verrouille",
            font=ctk.CTkFont(size=10), text_color=C_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        rf = self._section(sf, "Sans fil")
        for key, label in WIRELESS.items():
            ctk.CTkRadioButton(rf, text=label, variable=self._wireless_var, value=key).pack(anchor="w", pady=4)

    def _step_finish(self) -> None:
        profile = self._build_profile()
        profile.sensors = profile.normalized_sensors()

        wrap = ctk.CTkFrame(self._body, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        self._step_header(
            wrap,
            "Votre configuration est prete",
            "Apercu du code, telechargement et export des fichiers.",
        )

        recap_frame = ctk.CTkFrame(wrap, fg_color=C_CARD2, corner_radius=12)
        recap_frame.pack(fill="x", pady=(0, 10))
        recap = (
            f"{profile.board_label()}  ·  "
            f"{', '.join(profile.sensor_labels()) or 'aucun capteur'}  ·  "
            f"{profile.display_label()}"
        )
        if profile.requires_rfid_unlock():
            recap += f"  ·  RFID {profile.rfid_uid}"
        ctk.CTkLabel(
            recap_frame, text=recap, font=ctk.CTkFont(size=12), text_color=C_TEXT,
            wraplength=660,
        ).pack(padx=16, pady=12)

        views = {
            "Code Arduino": generate_sketch(profile),
            "Branchement": generate_wiring(profile),
            "Modules": generate_dependencies(profile),
        }

        preview = ctk.CTkTextbox(
            wrap, height=200, font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#0d1117", text_color=C_TEXT, wrap="none",
        )

        seg = ctk.CTkSegmentedButton(
            wrap, values=list(views.keys()), fg_color=C_CARD2,
            selected_color=C_ACCENT, selected_hover_color="#0284d4",
            command=lambda c, box=preview, v=views: self._show_preview(box, v, c),
        )
        seg.pack(fill="x", pady=(0, 8))
        seg.set("Code Arduino")

        preview.pack(fill="x", pady=(0, 10))
        self._show_preview(preview, views, "Code Arduino")

        ctk.CTkLabel(
            wrap, text="Telecharger les fichiers",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w", pady=(0, 6))

        dl_grid = ctk.CTkFrame(wrap, fg_color="transparent")
        dl_grid.pack(fill="x", pady=(0, 8))
        dl_grid.grid_columnconfigure((0, 1), weight=1)

        for i, (filename, ext, label) in enumerate(EXPORT_FILES):
            r, c = divmod(i, 2)
            cell = ctk.CTkFrame(dl_grid, fg_color=C_CARD2, corner_radius=10)
            cell.grid(row=r, column=c, sticky="ew", padx=(0, 6) if c == 0 else (6, 0), pady=4)
            cell.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                cell, text=label, font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))
            ctk.CTkLabel(
                cell, text=filename, font=ctk.CTkFont(family="Consolas", size=11),
                text_color=C_ACCENT,
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 0))
            ctk.CTkButton(
                cell, text=f"Telecharger {ext}", height=28, width=140,
                fg_color=C_CARD, hover_color="#263044",
                command=lambda f=filename, e=ext, lb=label, pr=profile: self._download_file(pr, f, e, lb),
            ).grid(row=2, column=0, sticky="w", padx=12, pady=(8, 10))

        ctk.CTkButton(
            wrap, text="Tout enregistrer dans Documents\\Stormer",
            height=38, fg_color=C_GREEN, hover_color="#16a34a",
            command=lambda: self._export(profile),
        ).pack(fill="x")

    @staticmethod
    def _show_preview(box: ctk.CTkTextbox, views: dict[str, str], choice: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", views.get(choice, ""))
        box.configure(state="disabled")

    def _build_profile(self) -> HardwareProfile:
        access = self._access_var.get()
        profile = HardwareProfile(
            board=self._board_var.get(),
            sensors=[k for k, v in self._sensor_vars.items() if v.get()],
            display=self._display_var.get(),
            wireless=self._wireless_var.get(),
            access=access,
            output=self._output_var.get(),
            rfid_uid=self._rfid_uid if access != "none" else "",
        )
        profile.ensure_rfid_uid()
        self._rfid_uid = profile.rfid_uid
        return profile

    def _validate_step(self) -> bool:
        if self._step == 1 and not any(v.get() for v in self._sensor_vars.values()):
            messagebox.showwarning("Capteurs", "Selectionnez au moins un capteur.")
            return False
        return True

    def _next_step(self) -> None:
        if not self._validate_step():
            return
        if self._step < 3:
            self._show_step(self._step + 1)
        else:
            self._finish()

    def _prev_step(self) -> None:
        if self._step > 0:
            self._show_step(self._step - 1)

    def _open_export_folder(self, folder) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except OSError:
            pass

    def _download_file(self, profile: HardwareProfile, filename: str, ext: str, label: str) -> None:
        p = profile
        p.sensors = profile.normalized_sensors()
        path = filedialog.asksaveasfilename(
            parent=self.master,
            title=f"Enregistrer — {label}",
            defaultextension=ext,
            initialfile=filename,
            filetypes=[(f"Fichier {ext}", f"*{ext}"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(export_file_content(p, filename), encoding="utf-8")
            messagebox.showinfo("Telechargement", f"Fichier enregistre :\n{path}")
        except OSError as exc:
            messagebox.showerror("Erreur", str(exc))

    def _export(self, profile: HardwareProfile) -> None:
        p = profile
        p.sensors = profile.normalized_sensors()
        paths = export_generated_files(p)
        folder = export_dir()
        self._open_export_folder(folder)
        names = "\n".join(f"  {path.name}" for path in paths)
        messagebox.showinfo("Export", f"Fichiers enregistres dans :\n{folder}\n\n{names}")

    def _finish(self) -> None:
        profile = self._build_profile()
        profile.sensors = profile.normalized_sensors()
        save_profile(profile)
        try:
            export_generated_files(profile)
        except OSError:
            pass
        self.result = profile
        self._close()

    def _close(self) -> None:
        try:
            self.master.grab_release()
        except Exception:
            pass
        if isinstance(self.master, ctk.CTk):
            self.master.quit()
        else:
            self.master.destroy()

    def _on_close(self) -> None:
        if self._force and self.result is None:
            if not messagebox.askyesno("Quitter", "Configuration requise.\nQuitter Stormer ?"):
                return
        self.result = None
        self._close()


def run_setup_wizard(
    force: bool = False,
    parent: ctk.CTk | None = None,
    initial: HardwareProfile | None = None,
) -> HardwareProfile | None:
    """Lance le wizard. Si parent est fourni, fenetre modale (depuis l'app)."""
    if parent is None:
        root = ctk.CTk()
        ctk.set_appearance_mode("dark")
        wizard = SetupWizard(root, force=force, initial=initial)
        root.mainloop()
        result = wizard.result
        try:
            root.destroy()
        except Exception:
            pass
        return result

    top = ctk.CTkToplevel(parent)
    top.transient(parent)
    top.grab_set()
    top.lift()
    top.focus_force()
    wizard = SetupWizard(top, force=force, initial=initial or load_profile())
    parent.wait_window(top)
    return wizard.result
