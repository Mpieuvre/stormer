"""Installateur Stormer — style classique Windows."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from stormer.branding import apply_window_icon, installer_banner_png, license_txt, logo_png
from stormer.config import APP_NAME, APP_VERSION
from stormer.installer_core import default_install_dir, has_existing, install, launch_app, uninstall

# Style installateur classique
C_WIN_BG = "#f0f0f0"
C_PANEL = "#ffffff"
C_TEXT = "#1a1a1a"
C_MUTED = "#555555"
C_GREEN = "#008000"
C_GREEN_BAR = "#00a651"
C_SIDEBAR = "#1e293b"
C_BTN = "#e1e1e1"


class StormerInstaller(tk.Tk):
    STEPS = ("welcome", "license", "folder", "ready", "install", "done")

    def __init__(self):
        super().__init__()
        self.title(f"Installation de {APP_NAME} {APP_VERSION}")
        self.geometry("620x420")
        self.resizable(False, False)
        self.configure(bg=C_WIN_BG)
        apply_window_icon(self)

        self._step_idx = 0
        self._dir_var = tk.StringVar(value=str(default_install_dir()))
        self._accept_var = tk.BooleanVar(value=False)
        self._desktop_var = tk.BooleanVar(value=True)
        self._launch_var = tk.BooleanVar(value=True)
        self._install_dir = default_install_dir()
        self._banner_img: ImageTk.PhotoImage | None = None
        self._logo_img: ImageTk.PhotoImage | None = None

        self._build_layout()
        self._show_step(0)

    def _build_layout(self) -> None:
        # Bandeau lateral + contenu
        self._sidebar = tk.Frame(self, width=164, bg=C_SIDEBAR)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        banner = installer_banner_png()
        if banner.is_file():
            img = Image.open(banner)
            self._banner_img = ImageTk.PhotoImage(img)
            tk.Label(self._sidebar, image=self._banner_img, bg=C_SIDEBAR, bd=0).pack(fill="both", expand=True)
        else:
            tk.Label(
                self._sidebar, text="STORMER", fg="white", bg=C_SIDEBAR,
                font=("Segoe UI", 16, "bold"),
            ).pack(pady=40)

        right = tk.Frame(self, bg=C_WIN_BG)
        right.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(right, bg=C_PANEL, highlightbackground="#c0c0c0", highlightthickness=1)
        self._content.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        # Barre boutons classique
        btn_bar = tk.Frame(right, bg=C_WIN_BG)
        btn_bar.pack(fill="x", padx=12, pady=(0, 10))

        self._cancel_btn = tk.Button(
            btn_bar, text="Annuler", width=10, command=self.destroy,
            bg=C_BTN, relief="raised",
        )
        self._cancel_btn.pack(side="right", padx=(4, 0))

        self._next_btn = tk.Button(
            btn_bar, text="Suivant >", width=12, command=self._next,
            bg=C_BTN, relief="raised", default="active",
        )
        self._next_btn.pack(side="right", padx=4)

        self._back_btn = tk.Button(
            btn_bar, text="< Retour", width=10, command=self._prev,
            bg=C_BTN, relief="raised", state="disabled",
        )
        self._back_btn.pack(side="right", padx=4)

    def _clear_content(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

    def _header(self, title: str, subtitle: str = "") -> None:
        row = tk.Frame(self._content, bg=C_PANEL)
        row.pack(fill="x", padx=16, pady=(14, 8))
        logo_path = logo_png()
        if logo_path.is_file():
            img = Image.open(logo_path).resize((40, 40), Image.Resampling.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
            tk.Label(row, image=self._logo_img, bg=C_PANEL).pack(side="left", padx=(0, 10))
        txt = tk.Frame(row, bg=C_PANEL)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text=title, font=("Segoe UI", 12, "bold"), bg=C_PANEL, fg=C_TEXT, anchor="w").pack(fill="x")
        if subtitle:
            tk.Label(txt, text=subtitle, font=("Segoe UI", 9), bg=C_PANEL, fg=C_MUTED, anchor="w").pack(fill="x")

    def _show_step(self, idx: int) -> None:
        self._step_idx = idx
        self._back_btn.configure(state="normal" if idx > 0 and idx < 5 else "disabled")
        labels = {
            0: "Suivant >",
            1: "Suivant >",
            2: "Suivant >",
            3: "Installer",
            4: "",
            5: "Terminer",
        }
        self._next_btn.configure(text=labels.get(idx, "Suivant >"), state="normal")
        if idx == 4:
            self._next_btn.configure(state="disabled")
            self._back_btn.configure(state="disabled")
            self._cancel_btn.configure(state="disabled")

        self._clear_content()
        [
            self._page_welcome,
            self._page_license,
            self._page_folder,
            self._page_ready,
            self._page_install,
            self._page_done,
        ][idx]()

    def _page_welcome(self) -> None:
        self._header("Bienvenue dans l'assistant d'installation de Stormer", f"Version {APP_VERSION}")
        extra = ""
        if has_existing(default_install_dir()):
            extra = (
                "\n\nUne version de Stormer est deja installee.\n"
                "Elle sera desinstallee automatiquement avant la nouvelle installation."
            )
        tk.Label(
            self._content,
            text=(
                "Cet assistant va installer Stormer sur votre ordinateur.\n\n"
                "Stormer permet d'acquerir, afficher et analyser les donnees\n"
                "de vos capteurs Arduino (temperature, humidite, etc.).\n\n"
                "Il est recommande de fermer les autres applications\n"
                "avant de continuer.\n\n"
                "Cliquez sur Suivant pour continuer."
                f"{extra}"
            ),
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT, justify="left", anchor="nw",
        ).pack(fill="both", expand=True, padx=20, pady=8)

    def _page_license(self) -> None:
        self._header("Contrat de licence", "Vous devez accepter le contrat pour continuer.")
        text_frame = tk.Frame(self._content, bg=C_PANEL)
        text_frame.pack(fill="both", expand=True, padx=16, pady=4)

        scroll = tk.Scrollbar(text_frame)
        scroll.pack(side="right", fill="y")
        box = tk.Text(
            text_frame, wrap="word", height=12, font=("Consolas", 9),
            yscrollcommand=scroll.set, bg="#fafafa", fg=C_TEXT, relief="sunken", bd=1,
        )
        box.pack(side="left", fill="both", expand=True)
        scroll.config(command=box.yview)

        lic = license_txt()
        content = lic.read_text(encoding="utf-8") if lic.is_file() else "Licence non trouvee."
        box.insert("1.0", content)
        box.configure(state="disabled")

        tk.Checkbutton(
            self._content,
            text="J'accepte les termes du contrat de licence",
            variable=self._accept_var,
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT,
            activebackground=C_PANEL,
        ).pack(anchor="w", padx=18, pady=(4, 10))

    def _page_folder(self) -> None:
        self._header("Destination", "Choisissez le dossier d'installation.")
        tk.Label(
            self._content, text="Stormer sera installe dans le dossier suivant :",
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT, anchor="w",
        ).pack(fill="x", padx=18, pady=(8, 4))

        row = tk.Frame(self._content, bg=C_PANEL)
        row.pack(fill="x", padx=18, pady=4)
        tk.Entry(row, textvariable=self._dir_var, font=("Segoe UI", 9), width=48).pack(side="left", padx=(0, 6))
        tk.Button(row, text="Parcourir...", command=self._browse, bg=C_BTN).pack(side="left")

        tk.Checkbutton(
            self._content, text="Creer un raccourci sur le Bureau",
            variable=self._desktop_var, font=("Segoe UI", 9), bg=C_PANEL,
        ).pack(anchor="w", padx=18, pady=(12, 2))
        tk.Checkbutton(
            self._content, text="Lancer Stormer a la fin de l'installation",
            variable=self._launch_var, font=("Segoe UI", 9), bg=C_PANEL,
        ).pack(anchor="w", padx=18, pady=2)

        tk.Label(
            self._content,
            text="Espace requis : environ 120 Mo",
            font=("Segoe UI", 8), bg=C_PANEL, fg=C_MUTED,
        ).pack(anchor="w", padx=18, pady=(12, 0))

    def _page_ready(self) -> None:
        self._header("Pret a installer", "Verifiez les parametres avant de continuer.")
        reinstall = ""
        try:
            target = Path(self._dir_var.get().strip())
        except Exception:
            target = default_install_dir()
        if has_existing(target):
            reinstall = "Ancienne version : sera supprimee automatiquement.\n\n"
        tk.Label(
            self._content,
            text=(
                f"L'assistant va installer {APP_NAME} {APP_VERSION}.\n\n"
                f"{reinstall}"
                f"Dossier : {self._dir_var.get()}\n"
                f"Raccourci Bureau : {'Oui' if self._desktop_var.get() else 'Non'}\n"
                f"Menu Demarrer : Oui\n"
                f"Documents\\Stormer : exports et sessions (conservees)\n\n"
                "Cliquez sur Installer pour demarrer l'installation."
            ),
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT, justify="left", anchor="nw",
        ).pack(fill="both", expand=True, padx=20, pady=8)

    def _page_install(self) -> None:
        self._header("Installation en cours", "Veuillez patienter…")
        tk.Label(
            self._content, text="Installation de Stormer…",
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT,
        ).pack(anchor="w", padx=18, pady=(8, 12))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#e0e0e0",
            background=C_GREEN_BAR,
            bordercolor="#c0c0c0",
            lightcolor=C_GREEN_BAR,
            darkcolor=C_GREEN,
            thickness=22,
        )
        self._progress = ttk.Progressbar(
            self._content, style="Green.Horizontal.TProgressbar",
            length=380, mode="determinate", maximum=100,
        )
        self._progress.pack(padx=18, pady=4)

        self._status = tk.StringVar(value="Preparation…")
        tk.Label(
            self._content, textvariable=self._status,
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_MUTED,
        ).pack(anchor="w", padx=18, pady=8)

        self._file_lbl = tk.Label(
            self._content, text="", font=("Segoe UI", 8), bg=C_PANEL, fg=C_MUTED, anchor="w",
        )
        self._file_lbl.pack(fill="x", padx=18)

        self.after(300, self._run_install)

    def _page_done(self) -> None:
        self._header("Installation terminee", "Stormer a ete installe avec succes.")
        tk.Label(
            self._content,
            text=(
                "L'assistant a termine l'installation de Stormer.\n\n"
                f"Dossier : {self._install_dir}\n"
                "Raccourci : Bureau\\Stormer.lnk\n\n"
                "Cliquez sur Terminer pour quitter l'assistant."
            ),
            font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT, justify="left",
        ).pack(fill="both", expand=True, padx=20, pady=8)
        self._cancel_btn.configure(state="disabled")

    def _browse(self) -> None:
        path = filedialog.askdirectory(title="Dossier d'installation")
        if path:
            self._dir_var.set(path)

    def _tick_progress(self, val: int, status: str, file: str = "") -> None:
        self._progress["value"] = val
        self._status.set(status)
        self._file_lbl.configure(text=file)
        self.update_idletasks()

    def _run_install(self) -> None:
        try:
            self._install_dir = Path(self._dir_var.get().strip())
        except Exception:
            self._install_dir = default_install_dir()

        try:
            if has_existing(self._install_dir):
                self._tick_progress(10, "Desinstallation de l'ancienne version…", str(self._install_dir))
                self.update()
                uninstall(self._install_dir)

            self._tick_progress(25, "Creation des dossiers…", "Documents\\Stormer")
            self.update()
            self._tick_progress(50, "Copie de Stormer.exe…", str(self._install_dir / "Stormer.exe"))
            self.update()

            install(
                self._install_dir,
                desktop_shortcut=self._desktop_var.get(),
                start_menu_shortcut=True,
            )

            self._tick_progress(85, "Creation des raccourcis…", "Bureau\\Stormer.lnk")
            self.update()
            self._tick_progress(100, "Installation terminee.", "")

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
            messagebox.showwarning(
                "Contrat de licence",
                "Vous devez accepter le contrat de licence pour continuer.",
            )
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
