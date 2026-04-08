from __future__ import annotations

import ctypes
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from headtoys.config import AppConfig
from headtoys.constants import (
    APP_ACCENT_COLOR,
    APP_BORDER,
    APP_CARD,
    APP_MUTED,
    APP_NAME,
    APP_PRIMARY_COLOR,
    APP_PRIMARY_DARK,
    APP_SURFACE,
    APP_SURFACE_ALT,
    APP_TEXT,
    INSTALL_ROOT,
    LAUNCHER_EXE_NAME,
    UNINSTALLER_EXE_NAME,
)
from headtoys.indexer import get_available_categories
from headtoys.install_tasks import apply_installation, copy_payload_files, stop_running_launcher


def resolve_payload_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidate = base / "payload"
        if candidate.exists():
            return candidate
    local_candidate = ROOT_DIR / "payload"
    if local_candidate.exists():
        return local_candidate
    raise FileNotFoundError("A pasta payload não foi encontrada.")


class InstallerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Instalador HeadToys")
        self.geometry("900x720")
        self.resizable(False, False)
        self.configure(fg_color=APP_SURFACE)
        self.install_dir_var = ctk.StringVar(value=str(INSTALL_ROOT))
        self.clients_root_var = ctk.StringVar(value="")
        self.auto_start_var = ctk.BooleanVar(value=True)
        self.start_minimized_var = ctk.BooleanVar(value=True)
        self.launch_now_var = ctk.BooleanVar(value=True)
        self.status_var = ctk.StringVar(value="Selecione a pasta dos clientes e as categorias que entram no buscador.")
        self.category_vars: dict[str, ctk.BooleanVar] = {}
        self.category_frame: ctk.CTkScrollableFrame | None = None
        self.install_button: ctk.CTkButton | None = None
        self._build()
        self.after(200, self._check_admin)

    def _check_admin(self) -> None:
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            self.status_var.set("Este instalador precisa ser executado como administrador para gravar em Program Files (x86).")

    def _build(self) -> None:
        shell = ctk.CTkFrame(self, fg_color=APP_SURFACE, corner_radius=0)
        shell.pack(fill="both", expand=True, padx=26, pady=26)

        hero = ctk.CTkFrame(shell, fg_color=APP_CARD, border_width=1, border_color=APP_BORDER, corner_radius=28)
        hero.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(hero, text="Instalar HeadToys", font=ctk.CTkFont(size=30, weight="bold"), text_color=APP_TEXT).pack(anchor="w", padx=28, pady=(24, 6))
        ctk.CTkLabel(
            hero,
            text="O instalador copia o launcher para Program Files, cria a pasta Login Clientes na área de trabalho, registra a inicialização com o Windows e já deixa o buscador pronto na bandeja.",
            font=ctk.CTkFont(size=14),
            text_color=APP_MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=28, pady=(0, 24))

        card = ctk.CTkFrame(shell, fg_color=APP_CARD, border_width=1, border_color=APP_BORDER, corner_radius=28)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(card, text="Diretório de instalação", font=ctk.CTkFont(size=15, weight="bold"), text_color=APP_TEXT).pack(anchor="w", padx=26, pady=(24, 8))
        install_row = ctk.CTkFrame(card, fg_color="transparent")
        install_row.pack(fill="x", padx=26)
        ctk.CTkEntry(
            install_row,
            textvariable=self.install_dir_var,
            height=44,
            border_width=1,
            border_color=APP_BORDER,
            fg_color=APP_SURFACE_ALT,
            text_color=APP_TEXT,
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            install_row,
            text="Alterar",
            width=120,
            height=44,
            fg_color="transparent",
            border_width=1,
            border_color=APP_BORDER,
            hover_color=APP_SURFACE,
            command=self._browse_install_dir,
        ).pack(side="left", padx=(12, 0))

        ctk.CTkLabel(card, text="Pasta principal dos clientes", font=ctk.CTkFont(size=15, weight="bold"), text_color=APP_TEXT).pack(anchor="w", padx=26, pady=(20, 8))
        source_row = ctk.CTkFrame(card, fg_color="transparent")
        source_row.pack(fill="x", padx=26)
        ctk.CTkEntry(
            source_row,
            textvariable=self.clients_root_var,
            height=44,
            border_width=1,
            border_color=APP_BORDER,
            fg_color=APP_SURFACE_ALT,
            text_color=APP_TEXT,
            placeholder_text=r"C:\Users\...\OneDrive\Pastinha Clientes",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            source_row,
            text="Procurar",
            width=120,
            height=44,
            fg_color=APP_PRIMARY_COLOR,
            hover_color=APP_PRIMARY_DARK,
            command=self._browse_clients_root,
        ).pack(side="left", padx=(12, 0))
        ctk.CTkButton(
            card,
            text="Detectar categorias",
            height=38,
            fg_color=APP_ACCENT_COLOR,
            hover_color="#6D0010",
            command=self._refresh_categories,
        ).pack(anchor="w", padx=26, pady=(14, 18))

        ctk.CTkLabel(card, text="Categorias do buscador", font=ctk.CTkFont(size=15, weight="bold"), text_color=APP_TEXT).pack(anchor="w", padx=26, pady=(0, 8))
        self.category_frame = ctk.CTkScrollableFrame(card, fg_color=APP_SURFACE_ALT, border_width=1, border_color=APP_BORDER, corner_radius=22, height=260)
        self.category_frame.pack(fill="both", expand=True, padx=26)

        options = ctk.CTkFrame(card, fg_color="transparent")
        options.pack(fill="x", padx=26, pady=18)
        ctk.CTkCheckBox(options, text="Abrir com o Windows", variable=self.auto_start_var, fg_color=APP_PRIMARY_COLOR, hover_color=APP_PRIMARY_DARK, text_color=APP_TEXT).pack(anchor="w")
        ctk.CTkCheckBox(options, text="Iniciar oculto na bandeja", variable=self.start_minimized_var, fg_color=APP_PRIMARY_COLOR, hover_color=APP_PRIMARY_DARK, text_color=APP_TEXT).pack(anchor="w", pady=(10, 0))
        ctk.CTkCheckBox(options, text="Abrir o HeadToys ao concluir", variable=self.launch_now_var, fg_color=APP_PRIMARY_COLOR, hover_color=APP_PRIMARY_DARK, text_color=APP_TEXT).pack(anchor="w", pady=(10, 0))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=26, pady=(0, 24))
        ctk.CTkLabel(footer, textvariable=self.status_var, font=ctk.CTkFont(size=13), text_color=APP_MUTED, wraplength=560, justify="left").pack(side="left")
        self.install_button = ctk.CTkButton(footer, text="Instalar", width=150, height=46, fg_color=APP_PRIMARY_COLOR, hover_color=APP_PRIMARY_DARK, command=self._install)
        self.install_button.pack(side="right")

    def _browse_install_dir(self) -> None:
        selected = filedialog.askdirectory(title="Escolha a pasta de instalação", initialdir=str(INSTALL_ROOT.parent))
        if selected:
            self.install_dir_var.set(selected)

    def _browse_clients_root(self) -> None:
        selected = filedialog.askdirectory(title="Escolha a pasta principal dos clientes")
        if selected:
            self.clients_root_var.set(selected)
            self._refresh_categories()

    def _refresh_categories(self) -> None:
        root = Path(self.clients_root_var.get().strip())
        if self.category_frame is None:
            return
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        self.category_vars.clear()
        if not root.exists():
            self.status_var.set("Selecione uma pasta válida para detectar as categorias.")
            return
        categories = get_available_categories(root)
        if not categories:
            self.status_var.set("Nenhuma categoria encontrada na pasta selecionada.")
            return
        for category in categories:
            variable = ctk.BooleanVar(value=True)
            self.category_vars[category] = variable
            ctk.CTkCheckBox(
                self.category_frame,
                text=category,
                variable=variable,
                fg_color=APP_PRIMARY_COLOR,
                hover_color=APP_PRIMARY_DARK,
                text_color=APP_TEXT,
            ).pack(anchor="w", padx=14, pady=8)
        self.status_var.set(f"{len(categories)} categoria(s) detectada(s).")

    def _install(self) -> None:
        install_dir = Path(self.install_dir_var.get().strip())
        clients_root = Path(self.clients_root_var.get().strip())
        categories = [name for name, variable in self.category_vars.items() if variable.get()]
        if not install_dir:
            messagebox.showerror(APP_NAME, "Informe uma pasta de instalação.")
            return
        if not clients_root.exists():
            messagebox.showerror(APP_NAME, "Selecione uma pasta de clientes válida.")
            return
        if not categories:
            messagebox.showerror(APP_NAME, "Selecione pelo menos uma categoria.")
            return
        if self.install_button:
            self.install_button.configure(state="disabled")
        self.status_var.set("Copiando arquivos, registrando o Windows e montando a pasta Login Clientes...")
        threading.Thread(
            target=self._install_worker,
            args=(install_dir, clients_root, categories),
            name="HeadToysInstaller",
            daemon=True,
        ).start()

    def _install_worker(self, install_dir: Path, clients_root: Path, categories: list[str]) -> None:
        try:
            payload_dir = resolve_payload_dir()
            stop_running_launcher(LAUNCHER_EXE_NAME)
            copied = copy_payload_files(
                payload_dir,
                install_dir,
                [LAUNCHER_EXE_NAME, UNINSTALLER_EXE_NAME, "logo_buscador.ico", "logo_buscador.png"],
            )
            copied_map = {item.name: item for item in copied}
            config = AppConfig(
                clients_root=str(clients_root),
                install_dir=str(install_dir),
                included_categories=categories,
                auto_start=bool(self.auto_start_var.get()),
                start_minimized=bool(self.start_minimized_var.get()),
            )
            apply_installation(
                config,
                copied_map[LAUNCHER_EXE_NAME],
                copied_map[UNINSTALLER_EXE_NAME],
                copied_map["logo_buscador.ico"],
            )
            if self.launch_now_var.get():
                subprocess.Popen([str(copied_map[LAUNCHER_EXE_NAME]), "--background"], cwd=str(install_dir))
            self.after(0, lambda: self._finish_install(install_dir))
        except Exception as exc:
            self.after(0, lambda: self._fail_install(exc))

    def _finish_install(self, install_dir: Path) -> None:
        if self.install_button:
            self.install_button.configure(state="normal")
        self.status_var.set("Instalação concluída.")
        messagebox.showinfo(
            APP_NAME,
            "Instalação concluída com sucesso.\n\n"
            f"Arquivos instalados em:\n{install_dir}\n\n"
            "O HeadToys já está pronto para usar com Alt + Espaço.",
        )
        self.destroy()

    def _fail_install(self, error: Exception) -> None:
        if self.install_button:
            self.install_button.configure(state="normal")
        self.status_var.set("Falha na instalação.")
        messagebox.showerror(APP_NAME, f"Não foi possível concluir a instalação.\n\n{error}")


def main() -> None:
    window = InstallerWindow()
    window.mainloop()


if __name__ == "__main__":
    main()
