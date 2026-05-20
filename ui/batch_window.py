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
        pass

    def _add_tracks(self):
        pass

    def _start_batch(self):
        pass
