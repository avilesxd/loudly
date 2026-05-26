import sys
import threading
from pathlib import Path

import customtkinter as ctk

from services import updater
from version import APP_VERSION


def _resource(relative: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
    return str(base / relative)


def check_for_updates(root: ctk.CTk) -> None:
    threading.Thread(target=_worker, args=(root,), daemon=True).start()


def _worker(root: ctk.CTk) -> None:
    result = updater.fetch_latest()
    if result is None:
        return
    tag, url = result
    if not updater.is_newer(tag):
        return
    root.after(0, lambda: _UpdateDialog(root, tag, url))


class _UpdateDialog(ctk.CTkToplevel):
    def __init__(self, root: ctk.CTk, new_version: str, url: str):
        super().__init__(root)
        self._root = root
        self._url = url

        self.title("Actualización disponible")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        w, h = 440, 230
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.after(250, lambda: self.iconbitmap(_resource("assets/loudly.ico")))

        ctk.CTkLabel(
            self,
            text=f"Nueva versión disponible: {new_version}",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(28, 6))

        ctk.CTkLabel(
            self,
            text=f"Versión actual: {APP_VERSION}   →   {new_version}",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            self,
            text="La app se reiniciará automáticamente al terminar.",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 10))

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self._status.pack()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=14)

        self._update_btn = ctk.CTkButton(
            btn_frame,
            text="Actualizar ahora",
            width=150,
            command=self._start_download,
        )
        self._update_btn.pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Más tarde",
            width=110,
            fg_color="gray30",
            hover_color="gray20",
            command=self.destroy,
        ).pack(side="left", padx=10)

    def _windows_set_titlebar_color(self, color_mode: str) -> None:
        # focus_get() → nametowidget() crashes with TypeError on certain Python
        # versions when the root widget is focused. Catch it so the dialog stays
        # visible (withdraw() on line 245 of ctk_toplevel is never reached before
        # the crash, so the window is still shown).
        try:
            super()._windows_set_titlebar_color(color_mode)
        except TypeError:
            pass

    def _start_download(self) -> None:
        self._update_btn.configure(state="disabled")
        self._status.configure(text="Descargando...")
        threading.Thread(target=self._download, daemon=True).start()

    def _download(self) -> None:
        try:
            tmp_exe = updater.download_update(self._url, on_progress=self._on_progress)
        except Exception as exc:
            self.after(0, lambda e=exc: self._status.configure(text=f"Error: {e}"))
            return
        self.after(0, lambda: self._finish(tmp_exe))

    def _on_progress(self, pct: int) -> None:
        self.after(0, lambda p=pct: self._status.configure(text=f"Descargando... {p}%"))

    def _finish(self, tmp_exe: str) -> None:
        should_exit = updater.apply_update(tmp_exe)
        if should_exit:
            self._root.destroy()
