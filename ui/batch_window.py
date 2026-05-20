import os
import tempfile
import threading
from dataclasses import dataclass
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
            any(item.status == "pending" for item in self._items)
            and self._ref_path is not None
            and (self._worker_thread is None or not self._worker_thread.is_alive())
        )
        self._process_btn.configure(state="normal" if can_run else "disabled")

    def _safe_after(self, ms: int, func) -> None:
        try:
            if self.winfo_exists():
                self.after(ms, func)
        except Exception:
            pass

    def _start_batch(self):
        self._cancel = False
        self._process_btn.configure(state="disabled", text="⏳ Procesando…")
        self._status_label.configure(text="Procesando…", text_color="#888888")
        self._worker_thread = threading.Thread(
            target=self._process_all, daemon=True
        )
        self._worker_thread.start()

    def _process_all(self):
        pending = [
            (i, item) for i, item in enumerate(self._items)
            if item.status == "pending"
        ]
        total = len(pending)

        for done_count, (idx, item) in enumerate(pending, start=1):
            if self._cancel:
                break

            self._safe_after(0, lambda i=idx: self._set_row_status(
                i, "⚙️ procesando…", "#f59e0b"
            ))

            tmp_in = tmp_out = None
            try:
                audio, sr = load_audio(item.path)

                ref_info = sf.info(self._ref_path)
                if ref_info.samplerate != sr:
                    raise ValueError(
                        f"Sample rate mismatch: track={sr} Hz, "
                        f"ref={ref_info.samplerate} Hz"
                    )

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_in = f.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_out = f.name

                sf.write(tmp_in, audio.T, sr, subtype="PCM_24")
                apply_automaster(tmp_in, self._ref_path, tmp_out)

                mastered, _ = load_audio(tmp_out)
                out_path = _remastered_path(item.path)
                sf.write(out_path, mastered.T, sr, subtype="PCM_24")

                item.status = "done"
                self._safe_after(0, lambda i=idx: self._set_row_status(
                    i, "✅ listo", "#4ade80"
                ))

            except Exception as e:
                msg = str(e)[:60]
                item.status = "error"
                item.message = msg
                self._safe_after(0, lambda i=idx, m=msg: self._set_row_status(
                    i, f"❌ {m}", "#ef4444"
                ))

            finally:
                for p in (tmp_in, tmp_out):
                    if p and os.path.exists(p):
                        try:
                            os.unlink(p)
                        except OSError:
                            pass

            self._safe_after(0, lambda n=done_count, t=total: self._status_label.configure(
                text=f"{n}/{t} procesados", text_color="#888888"
            ))

        if not self._cancel:
            done = sum(1 for item in self._items if item.status == "done")
            errors = sum(1 for item in self._items if item.status == "error")
            self._safe_after(0, lambda d=done, e=errors: self._on_batch_done(d, e))

    def _set_row_status(self, idx: int, text: str, color: str):
        if idx < len(self._rows):
            self._rows[idx]["status"].configure(text=text, text_color=color)

    def _on_batch_done(self, done: int, errors: int):
        self._process_btn.configure(text="⚡ Procesar todos")
        self._refresh_process_btn()
        if errors == 0:
            self._status_label.configure(
                text=f"✅ {done} track(s) exportados exitosamente",
                text_color="#4ade80",
            )
        else:
            self._status_label.configure(
                text=f"✅ {done} listo(s) — ❌ {errors} con error",
                text_color="#f59e0b",
            )

    def _on_close(self):
        self._cancel = True
        self.destroy()
