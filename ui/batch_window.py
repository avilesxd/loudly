import os
import tempfile
import threading
from dataclasses import dataclass, field
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk
import soundfile as sf

from audio.automaster import apply_automaster
from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


@dataclass
class BatchItem:
    path: str
    status: Literal["pending", "processing", "done", "error"] = "pending"
    message: str = ""


def _remastered_path(source_path: str) -> str:
    stem, _ = os.path.splitext(source_path)
    return stem + "_remastered.wav"


class BatchWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Batch Processing")
        self.geometry("620x480")
        self.resizable(False, False)

        self._items: list[BatchItem] = []
        self._rows: list[dict] = []  # {"name": CTkLabel, "status": CTkLabel}
        self._ref_path: str | None = None
        self._cancel = False
        self._worker_thread: threading.Thread | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Reference row
        ref_frame = ctk.CTkFrame(self, fg_color="transparent")
        ref_frame.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            ref_frame,
            text="Referencia:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self._ref_label = ctk.CTkLabel(
            ref_frame,
            text="no seleccionada",
            text_color="#888888",
            font=ctk.CTkFont(size=12),
        )
        self._ref_label.pack(side="left", padx=10)

        ctk.CTkButton(
            ref_frame,
            text="Elegir",
            width=70,
            command=self._pick_reference,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
        ).pack(side="right")

        # Scrollable track list
        self._list_frame = ctk.CTkScrollableFrame(self, height=280)
        self._list_frame.pack(fill="x", padx=20, pady=8)

        self._empty_label = ctk.CTkLabel(
            self._list_frame,
            text="No hay tracks cargados",
            text_color="#555555",
            font=ctk.CTkFont(size=12),
        )
        self._empty_label.pack(pady=20)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=12)

        ctk.CTkButton(
            btn_frame,
            text="+ Agregar tracks",
            command=self._add_tracks,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
            width=160,
        ).pack(side="left")

        self._process_btn = ctk.CTkButton(
            btn_frame,
            text="⚡ Procesar todos",
            command=self._start_batch,
            state="disabled",
            width=180,
        )
        self._process_btn.pack(side="right")

        self._status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="#888888"
        )
        self._status_label.pack(pady=(0, 8))

    def _pick_reference(self):
        path = filedialog.askopenfilename(
            parent=self, filetypes=SUPPORTED, title="Seleccionar referencia"
        )
        if not path:
            return
        self._ref_path = path
        self._ref_label.configure(
            text=os.path.basename(path), text_color="#60a5fa"
        )
        self._refresh_process_btn()

    def _add_tracks(self):
        paths = filedialog.askopenfilenames(
            parent=self, filetypes=SUPPORTED, title="Seleccionar tracks"
        )
        if not paths:
            return
        existing = {item.path for item in self._items}
        for path in paths:
            if path in existing:
                continue
            item = BatchItem(path=path)
            self._items.append(item)
            existing.add(path)
            self._add_row(item)
        if self._items:
            self._empty_label.pack_forget()
        self._refresh_process_btn()

    def _add_row(self, item: BatchItem):
        row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        name_lbl = ctk.CTkLabel(
            row,
            text=os.path.basename(item.path),
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=380,
        )
        name_lbl.pack(side="left")

        status_lbl = ctk.CTkLabel(
            row,
            text="⏳ en cola",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            width=160,
            anchor="w",
        )
        status_lbl.pack(side="left")

        self._rows.append({"name": name_lbl, "status": status_lbl})

    def _refresh_process_btn(self):
        can_run = (
            bool(self._items)
            and self._ref_path is not None
            and (self._worker_thread is None or not self._worker_thread.is_alive())
        )
        self._process_btn.configure(state="normal" if can_run else "disabled")

    def _start_batch(self):
        pass

    def _on_close(self):
        self._cancel = True
        self.destroy()
