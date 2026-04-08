from __future__ import annotations

import sys
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from headtoys.config import load_config
from headtoys.constants import (
    APP_BORDER,
    APP_CARD,
    APP_MUTED,
    APP_NAME,
    APP_PRIMARY_COLOR,
    APP_PRIMARY_DARK,
    APP_SURFACE,
    APP_TEXT,
    DESKTOP_FOLDER_NAME,
    LAUNCHER_EXE_NAME,
)
from headtoys.install_tasks import remove_config_dir, remove_user_integrations, schedule_install_dir_removal, stop_running_launcher


class UninstallerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Desinstalar HeadToys")
        self.geometry("640x360")
        self.resizable(False, False)
        self.configure(fg_color=APP_SURFACE)
        self.status_var = ctk.StringVar(value="A desinstalação remove os atalhos, a inicialização automática e a configuração local do usuário.")
        self.button: ctk.CTkButton | None = None
        self._build()

    def _build(self) -> None:
        shell = ctk.CTkFrame(self, fg_color=APP_CARD, border_width=1, border_color=APP_BORDER, corner_radius=28)
        shell.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(shell, text="Desinstalar HeadToys", font=ctk.CTkFont(size=28, weight="bold"), text_color=APP_TEXT).pack(anchor="w", padx=28, pady=(24, 8))
        ctk.CTkLabel(
            shell,
            text="O diretório de instalação será removido após fechar este desinstalador. A pasta Login Clientes da área de trabalho e os dados do AppData também serão apagados.",
            font=ctk.CTkFont(size=14),
            text_color=APP_MUTED,
            wraplength=540,
            justify="left",
        ).pack(anchor="w", padx=28, pady=(0, 24))
        ctk.CTkLabel(shell, textvariable=self.status_var, font=ctk.CTkFont(size=13), text_color=APP_MUTED, wraplength=520, justify="left").pack(anchor="w", padx=28)
        self.button = ctk.CTkButton(shell, text="Desinstalar", width=150, height=46, fg_color=APP_PRIMARY_COLOR, hover_color=APP_PRIMARY_DARK, command=self._confirm_uninstall)
        self.button.pack(anchor="e", padx=28, pady=(28, 28))

    def _confirm_uninstall(self) -> None:
        accepted = messagebox.askyesno(APP_NAME, "Confirmar a remoção completa do HeadToys?")
        if not accepted:
            return
        if self.button:
            self.button.configure(state="disabled")
        self.status_var.set("Removendo integrações do Windows e limpando os arquivos do usuário...")
        threading.Thread(target=self._uninstall_worker, name="HeadToysUninstall", daemon=True).start()

    def _uninstall_worker(self) -> None:
        try:
            config = load_config()
            desktop_folder_name = config.desktop_folder_name or DESKTOP_FOLDER_NAME
            install_dir = Path(config.install_dir) if config.install_dir else Path(sys.executable).resolve().parent
            stop_running_launcher(LAUNCHER_EXE_NAME)
            remove_user_integrations(desktop_folder_name)
            remove_config_dir()
            schedule_install_dir_removal(install_dir)
            self.after(0, self._finish_uninstall)
        except Exception as exc:
            self.after(0, lambda: self._fail_uninstall(exc))

    def _finish_uninstall(self) -> None:
        self.status_var.set("Desinstalação concluída.")
        messagebox.showinfo(APP_NAME, "O HeadToys foi removido deste usuário.")
        self.destroy()

    def _fail_uninstall(self, error: Exception) -> None:
        if self.button:
            self.button.configure(state="normal")
        self.status_var.set("Falha ao desinstalar.")
        messagebox.showerror(APP_NAME, f"Não foi possível concluir a desinstalação.\n\n{error}")


def main() -> None:
    window = UninstallerWindow()
    window.mainloop()


if __name__ == "__main__":
    main()
