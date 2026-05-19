import customtkinter as ctk
import threading
import tempfile
import os
import numpy as np
import soundfile as sf
from tkinter import filedialog
from audio.automaster import apply_automaster
from audio.limiter import measure_lufs
from audio.loader import load_audio
from ui.components.player import AudioPlayer


class Step3Master(ctk.CTkFrame):
    def __init__(self, parent, session: dict, on_back):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_back = on_back
        self._build_ui()

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="both", expand=True, padx=20, pady=16)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        # Left column: auto-master + export
        left = ctk.CTkFrame(top, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            left,
            text="Auto-Master",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#7C3AED",
        ).pack(anchor="w", padx=14, pady=(12, 4))

        self._ref_info = ctk.CTkLabel(
            left,
            text="Sin referencia cargada",
            text_color="#888888",
            font=ctk.CTkFont(size=12),
        )
        self._ref_info.pack(padx=14, pady=4, anchor="w")

        self._automaster_btn = ctk.CTkButton(
            left,
            text="⚡ Aplicar Auto-Master",
            command=self._run_automaster,
            state="disabled",
        )
        self._automaster_btn.pack(padx=14, pady=8)

        self._status_label = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=12), wraplength=300
        )
        self._status_label.pack(padx=14, pady=4)

        # Export section
        export_frame = ctk.CTkFrame(left, corner_radius=8, fg_color="#111111")
        export_frame.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            export_frame,
            text="Exportar",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7C3AED",
        ).pack(anchor="w", padx=10, pady=(8, 4))

        fmt_row = ctk.CTkFrame(export_frame, fg_color="transparent")
        fmt_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(fmt_row, text="Formato:", font=ctk.CTkFont(size=12)).pack(
            side="left"
        )
        self._fmt_var = ctk.StringVar(value="WAV 24-bit")
        ctk.CTkOptionMenu(
            fmt_row, values=["WAV 24-bit", "FLAC"], variable=self._fmt_var, width=120
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            export_frame,
            text="💾 Guardar archivo",
            command=self._export,
            fg_color="#22c55e",
            hover_color="#16a34a",
            text_color="#000000",
        ).pack(padx=10, pady=(4, 12))

        # Right column: analysis + player
        right = ctk.CTkFrame(top, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            right,
            text="Análisis",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#7C3AED",
        ).pack(anchor="w", padx=14, pady=(12, 8))

        self._analysis_labels: dict[str, ctk.CTkLabel] = {}
        for key, label in [
            ("lufs", "LUFS integrado"),
            ("peak", "True Peak"),
            ("dr", "Dynamic Range"),
        ]:
            row = ctk.CTkFrame(right, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(
                row,
                text=label + ":",
                font=ctk.CTkFont(size=12),
                text_color="#888888",
                width=130,
            ).pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=12))
            val.pack(side="left")
            self._analysis_labels[key] = val

        self._player = AudioPlayer(right)
        self._player.pack(fill="x", padx=14, pady=16)

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(
            nav,
            text="← Atrás",
            command=self.on_back,
            width=100,
            fg_color="#2d2d3e",
            hover_color="#3d3d4e",
        ).pack(side="left")

    def on_enter(self):
        ref = self.session.get("reference_path")
        if ref:
            name = ref.split("/")[-1].split("\\")[-1]
            self._ref_info.configure(text=f"Referencia: {name}", text_color="#60a5fa")
            self._automaster_btn.configure(state="normal")
        else:
            self._ref_info.configure(
                text="Sin referencia — carga una en el paso 1 para usar Auto-Master",
                text_color="#f59e0b",
            )
            self._automaster_btn.configure(state="disabled")

        processed = self.session.get("processed_audio")
        if processed is not None:
            sr = self.session["sample_rate"]
            self._player.load(
                before=self.session["audio_data"],
                sample_rate=sr,
                after=self.session.get("mastered_audio"),
            )
            self._update_analysis(processed, sr)

    def _run_automaster(self):
        self._automaster_btn.configure(state="disabled", text="⏳ Procesando…")
        self._status_label.configure(
            text="Aplicando matchering, puede tardar unos segundos…",
            text_color="#888888",
        )

        def _work():
            try:
                processed = self.session["processed_audio"]
                sr = self.session["sample_rate"]
                ref_path = self.session["reference_path"]

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_in = f.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_out = f.name

                sf.write(tmp_in, processed.T, sr, subtype="PCM_24")
                apply_automaster(tmp_in, ref_path, tmp_out)

                mastered, _ = load_audio(tmp_out)
                self.session["mastered_audio"] = mastered
                os.unlink(tmp_in)
                os.unlink(tmp_out)

                self.after(0, lambda: self._on_automaster_done(mastered, sr))
            except Exception as e:
                self.after(0, lambda: self._on_automaster_error(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_automaster_done(self, mastered: np.ndarray, sr: int):
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(
            text="✅ Auto-master aplicado", text_color="#4ade80"
        )
        self._player.set_after(mastered)
        self._update_analysis(mastered, sr)

    def _on_automaster_error(self, error: str):
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(text=f"Error: {error}", text_color="#ef4444")

    def _update_analysis(self, audio: np.ndarray, sr: int):
        lufs = measure_lufs(audio, sr)
        peak = float(np.max(np.abs(audio)))
        peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
        dr = float(audio.std())

        self._analysis_labels["lufs"].configure(
            text=f"{lufs:.1f} LUFS", text_color="#4ade80"
        )
        self._analysis_labels["peak"].configure(
            text=f"{peak_db:.1f} dBTP",
            text_color="#4ade80" if peak_db < -0.1 else "#ef4444",
        )
        self._analysis_labels["dr"].configure(
            text=f"{dr * 100:.1f} DR", text_color="#aaaaaa"
        )

    def _export(self):
        audio = self.session.get("mastered_audio")
        if audio is None:
            audio = self.session.get("processed_audio")
        if audio is None:
            return
        sr = self.session["sample_rate"]
        fmt = self._fmt_var.get()

        ext = ".wav" if "WAV" in fmt else ".flac"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=ext,
            filetypes=(
                [("WAV", "*.wav"), ("FLAC", "*.flac")]
                if ext == ".wav"
                else [("FLAC", "*.flac"), ("WAV", "*.wav")]
            ),
            initialfile="mastered" + ext,
        )
        if not path:
            return

        subtype = "PCM_24" if "WAV" in fmt else None
        sf.write(path, audio.T, sr, subtype=subtype)
        self._status_label.configure(
            text=f"💾 Guardado: {path.split('/')[-1].split(chr(92))[-1]}",
            text_color="#4ade80",
        )
