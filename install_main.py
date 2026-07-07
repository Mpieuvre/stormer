"""Installateur Stormer — interface moderne."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from stormer.branding import apply_window_icon, license_txt, load_ctk_image
from stormer.config import APP_NAME, APP_VERSION
from stormer.installer_core import default_install_dir, has_existing, install, launch_app, uninstall

C_BG = "#0b0f14"
C_CARD = "#151b26"
C_CARD2 = "#1c2433"
C_ACCENT = "#029CFF"
C_ACCENT_DIM = "#1E2025"
C_GREEN = "#22c55e"
C_TEXT = "#e2e8f0"
C_MUTED = "#64748b"

STEP_LABELS = ("Bienvenue", "Licence", "Dossier", "Pret", "Installation", "Termine")


class StormerInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(f"Installation — {APP_NAME} {APP_VERSION}")
        self.geometry("720x520")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        apply_window_icon(self)

        self._step_idx = 0
        self._dir_var = tk.StringVar(value=str(default_install_dir()))
        self._accept_var = tk.BooleanVar(value=False)
        self._desktop_var = tk.BooleanVar(value=True)
        self._launch_var = tk.BooleanVar(value=True)
        self._install_dir = default_install_dir()
        self._step_pills: list[ctk.CTkLabel] = []
        self._progress: ctk.CTkProgressBar | None = None
        self._status_var = tk.StringVar(value="")

        self._build_layout()
        self._show_step(0)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, fg_color=C_ACCENT_DIM, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkFrame(sidebar, fg_color=C_ACCENT, height=4, corner_radius=0).pack(fill="x")

        logo_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_box.pack(pady=(28, 20))
        logo = load_ctk_image(56)
        if logo:
            ctk.CTkLabel(logo_box, text="", image=logo).pack()
        ctk.CTkLabel(
            logo_box, text="STORMER", font=ctk.CTkFont(size=20, weight="bold"), text_color=C_ACCENT,
        ).pack(pady=(8, 0))
        ctk.CTkLabel(
            logo_box, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).pack()

        for i, label in enumerate(STEP_LABELS[:5]):
            pill = ctk.CTkLabel(
                sidebar, text=f"  {i + 1}. {label}  ",
                font=ctk.CTkFont(size=11), text_color=C_MUTED,
                anchor="w",
            )
            pill.pack(anchor="w", padx=16, pady=3)
            self._step_pills.append(pill)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=20, pady=16)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self._content = ctk.CTkFrame(right, fg_color=C_CARD, corner_radius=16)
        self._content.grid(row=0, column=0, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(1, weight=1)

        self._title_lbl = ctk.CTkLabel(
            self._content, text="", font=ctk.CTkFont(size=20, weight="bold"), text_color=C_TEXT,
        )
        self._title_lbl.grid(row=0, column=0, sticky="w", padx=24, pady=(22, 4))

        self._body = ctk.CTkFrame(self._content, fg_color="transparent")
        self._body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

        footer = ctk.CTkFrame(right, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(1, weight=1)

        self._back_btn = ctk.CTkButton(
            footer, text="Retour", width=100, height=36,
            fg_color=C_CARD2, hover_color="#263044", command=self._prev,
        )
        self._back_btn.grid(row=0, column=0)

        self._next_btn = ctk.CTkButton(
            footer, text="Suivant", width=120, height=36,
            fg_color=C_ACCENT, hover_color="#0284d4", command=self._next,
        )
        self._next_btn.grid(row=0, column=2)

    def _clear_body(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()

    def _show_step(self, idx: int) -> None:
        self._step_idx = idx
        self._back_btn.configure(state="normal" if idx > 0 and idx < 5 else "disabled")
        next_labels = {0: "Suivant", 1: "Suivant", 2: "Suivant", 3: "Installer", 4: "", 5: "Terminer"}
        self._next_btn.configure(text=next_labels.get(idx, "Suivant"), state="normal")
        if idx == 4:
            self._next_btn.configure(state="disabled")
            self._back_btn.configure(state="disabled")

        for i, pill in enumerate(self._step_pills):
            if i == idx:
                pill.configure(text_color=C_ACCENT, font=ctk.CTkFont(size=11, weight="bold"))
            elif i < idx:
                pill.configure(text_color=C_GREEN, font=ctk.CTkFont(size=11))
            else:
                pill.configure(text_color=C_MUTED, font=ctk.CTkFont(size=11))

        self._clear_body()
        pages = [
            self._page_welcome,
            self._page_license,
            self._page_folder,
            self._page_ready,
            self._page_install,
            self._page_done,
        ]
        titles = [
            "Bienvenue",
            "Contrat de licence",
            "Destination",
            "Pret a installer",
            "Installation",
            "Termine",
        ]
        self._title_lbl.configure(text=titles[idx])
        pages[idx]()

    def _muted(self, parent, text: str, **kwargs) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=12), text_color=C_MUTED,
            justify="left", anchor="nw", wraplength=420, **kwargs,
        )

    def _page_welcome(self) -> None:
        extra = ""
        if has_existing(default_install_dir()):
            extra = "\n\nUne version existante sera remplacee automatiquement."
        self._muted(
            self._body,
            f"Cet assistant installe {APP_NAME} sur votre PC.\n\n"
            "Acquisition, affichage et analyse IA de vos capteurs Arduino.\n\n"
            "Fermez Stormer s'il est ouvert, puis cliquez sur Suivant."
            f"{extra}",
        ).pack(fill="both", expand=True)

    def _page_license(self) -> None:
        box = ctk.CTkTextbox(
            self._body, height=260, font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#0d1117", text_color=C_TEXT,
        )
        box.pack(fill="both", expand=True, pady=(0, 10))
        lic = license_txt()
        content = lic.read_text(encoding="utf-8") if lic.is_file() else "Licence non trouvee."
        box.insert("1.0", content)
        box.configure(state="disabled")
        ctk.CTkCheckBox(
            self._body, text="J'accepte les termes du contrat de licence",
            variable=self._accept_var, font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

    def _page_folder(self) -> None:
        self._muted(self._body, "Dossier d'installation :").pack(anchor="w", pady=(0, 8))
        row = ctk.CTkFrame(self._body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row, textvariable=self._dir_var, height=36).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(row, text="Parcourir", width=100, command=self._browse).grid(row=0, column=1)

        ctk.CTkCheckBox(
            self._body, text="Raccourci sur le Bureau", variable=self._desktop_var,
        ).pack(anchor="w", pady=4)
        ctk.CTkCheckBox(
            self._body, text="Lancer Stormer a la fin", variable=self._launch_var,
        ).pack(anchor="w", pady=4)
        self._muted(self._body, "Espace requis : ~120 Mo").pack(anchor="w", pady=(12, 0))

    def _page_ready(self) -> None:
        try:
            target = Path(self._dir_var.get().strip())
        except Exception:
            target = default_install_dir()
        reinstall = "Ancienne version : suppression automatique.\n\n" if has_existing(target) else ""
        self._muted(
            self._body,
            f"{reinstall}"
            f"Dossier : {self._dir_var.get()}\n"
            f"Raccourci Bureau : {'Oui' if self._desktop_var.get() else 'Non'}\n"
            f"Menu Demarrer : Oui\n"
            f"Documents\\Stormer : conserve\n\n"
            "Cliquez sur Installer pour demarrer.",
        ).pack(fill="both", expand=True)

    def _page_install(self) -> None:
        self._muted(self._body, "Installation en cours, veuillez patienter…").pack(anchor="w", pady=(0, 12))
        self._progress = ctk.CTkProgressBar(
            self._body, height=14, progress_color=C_GREEN, fg_color="#0d1117",
        )
        self._progress.pack(fill="x", pady=(0, 10))
        self._progress.set(0)
        ctk.CTkLabel(
            self._body, textvariable=self._status_var, font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).pack(anchor="w")
        self.after(300, self._run_install)

    def _page_done(self) -> None:
        self._muted(
            self._body,
            f"{APP_NAME} a ete installe avec succes.\n\n"
            f"Dossier : {self._install_dir}\n"
            f"Raccourci : Bureau\\{APP_NAME}.lnk\n\n"
            "Cliquez sur Terminer pour quitter.",
        ).pack(fill="both", expand=True)

    def _browse(self) -> None:
        path = filedialog.askdirectory(title="Dossier d'installation")
        if path:
            self._dir_var.set(path)

    def _tick_progress(self, val: float, status: str) -> None:
        if self._progress:
            self._progress.set(val)
        self._status_var.set(status)
        self.update_idletasks()

    def _run_install(self) -> None:
        try:
            self._install_dir = Path(self._dir_var.get().strip())
        except Exception:
            self._install_dir = default_install_dir()

        try:
            if has_existing(self._install_dir):
                self._tick_progress(0.1, "Desinstallation de l'ancienne version…")
                self.update()
                uninstall(self._install_dir)

            self._tick_progress(0.25, "Creation des dossiers…")
            self.update()
            self._tick_progress(0.5, "Copie de Stormer.exe…")
            self.update()

            install(
                self._install_dir,
                desktop_shortcut=self._desktop_var.get(),
                start_menu_shortcut=True,
            )

            self._tick_progress(0.85, "Creation des raccourcis…")
            self.update()
            self._tick_progress(1.0, "Installation terminee.")

            if self._launch_var.get():
                launch_app(self._install_dir)

            self.after(400, lambda: self._show_step(5))
        except Exception as exc:
            messagebox.showerror("Erreur d'installation", str(exc))
            self._show_step(3)

    def _next(self) -> None:
        step = self._step_idx
        if step == 5:
            self.destroy()
            return
        if step == 1 and not self._accept_var.get():
            messagebox.showwarning("Licence", "Acceptez le contrat pour continuer.")
            return
        if step == 2 and not self._dir_var.get().strip():
            messagebox.showwarning("Dossier", "Choisissez un dossier d'installation.")
            return
        if step == 3:
            self._show_step(4)
            return
        if step < 5:
            self._show_step(step + 1)

    def _prev(self) -> None:
        if self._step_idx > 0:
            self._show_step(self._step_idx - 1)


def run_installer() -> None:
    app = StormerInstaller()
    app.mainloop()


if __name__ == "__main__":
    run_installer()
