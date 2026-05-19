import os
import tempfile
import threading
from tkinter import filedialog

import customtkinter as ctk
import numpy as np
import soundfile as sf

from audio.automaster import apply_automaster
from audio.limiter import measure_lufs
from audio.loader import load_audio
from ui.components.player import AudioPlayer


class Step3Master(ctk.CTkFrame):
    """
    Paso 3 del wizard: auto-masterización por referencia, análisis
    comparativo y exportación.

    Layout de dos columnas:
        Izquierda: botón de Auto-Master, barra de progreso indeterminada durante el
                   procesamiento, y sección de exportación con selector de formato.
        Derecha: panel de análisis con métricas ANTES/DESPUÉS (LUFS, True Peak,
                 Dinámica)
                 y el reproductor ANTES/DESPUÉS.

    La exportación prioriza mastered_audio; si no existe (el usuario no usó
    Auto-Master),
    exporta processed_audio. Esto permite usar el paso 3 solo como panel de exportación
    sin necesidad de aplicar matchering.
    """

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

        self._progress = ctk.CTkProgressBar(left, mode="indeterminate", width=260)
        # not packed — shown only during processing

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
        ).pack(anchor="w", padx=14, pady=(12, 4))

        # Header row
        header_row = ctk.CTkFrame(right, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(header_row, text="", width=110).pack(side="left")
        ctk.CTkLabel(
            header_row,
            text="ANTES",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#60a5fa",
            width=80,
        ).pack(side="left")
        ctk.CTkLabel(
            header_row,
            text="DESPUÉS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a78bfa",
            width=80,
        ).pack(side="left")

        self._analysis_before: dict[str, ctk.CTkLabel] = {}
        self._analysis_after: dict[str, ctk.CTkLabel] = {}
        for key, label in [
            ("lufs", "LUFS"),
            ("peak", "True Peak"),
            ("dr", "Dinámica"),
        ]:
            row = ctk.CTkFrame(right, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(
                row,
                text=label + ":",
                font=ctk.CTkFont(size=12),
                text_color="#888888",
                width=110,
            ).pack(side="left")
            before_val = ctk.CTkLabel(
                row, text="—", font=ctk.CTkFont(size=12), width=80, text_color="#60a5fa"
            )
            before_val.pack(side="left")
            after_val = ctk.CTkLabel(
                row, text="—", font=ctk.CTkFont(size=12), width=80, text_color="#a78bfa"
            )
            after_val.pack(side="left")
            self._analysis_before[key] = before_val
            self._analysis_after[key] = after_val

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
        """
        Se llama al navegar hacia este paso.

        Habilita o deshabilita el botón de Auto-Master según si hay referencia
        en session. Actualiza el reproductor y el panel de análisis con el estado
        actual del session, lo que permite reflejar cambios de EQ si el usuario
        volvió al paso 2 y ajustó los controles.
        """
        ref = self.session.get("reference_path")
        if ref:
            name = os.path.basename(ref)
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
            mastered = self.session.get("mastered_audio")
            self._player.load(
                before=self.session["audio_data"], sample_rate=sr, after=mastered
            )
            self._update_analysis(processed, mastered, sr)

    def _run_automaster(self):
        """
        Serializa processed_audio a un WAV temporal y lanza matchering en un
        hilo daemon.

        matchering no opera sobre arrays en memoria; requiere rutas de archivos.
        El flujo es: processed_audio → WAV temporal (tmp_in) → matchering.process()
        → WAV resultado (tmp_out) → load_audio() → session["mastered_audio"].
        Los temporales se eliminan después de cargar el resultado, tanto en éxito
        como en error (el except en _work no limpia, pero son archivos del sistema).

        El botón se deshabilita para garantizar que solo corra un proceso a la vez.
        """
        self._automaster_btn.configure(state="disabled", text="⏳ Procesando…")
        self._status_label.configure(
            text="Aplicando matchering, puede tardar unos segundos…",
            text_color="#888888",
        )
        self._progress.pack(padx=14, pady=(0, 8))
        self._progress.start()

        def _work():
            tmp_in = None
            tmp_out = None
            try:
                processed = self.session["processed_audio"]
                sr = self.session["sample_rate"]
                ref_path = self.session["reference_path"]

                ref_info = sf.info(ref_path)
                if ref_info.samplerate != sr:
                    raise ValueError(
                        f"El sample rate de la referencia ({ref_info.samplerate} Hz) "
                        f"no coincide con el del track ({sr} Hz). "
                        f"Convertí la referencia a {sr} Hz antes de continuar."
                    )

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_in = f.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_out = f.name

                sf.write(tmp_in, processed.T, sr, subtype="PCM_24")
                apply_automaster(tmp_in, ref_path, tmp_out)

                mastered, _ = load_audio(tmp_out)
                self.session["mastered_audio"] = mastered

                self.after(0, lambda: self._on_automaster_done(mastered, sr))
            except Exception as e:
                self.after(0, lambda err=e: self._on_automaster_error(str(err)))
            finally:
                for path in (tmp_in, tmp_out):
                    if path and os.path.exists(path):
                        try:
                            os.unlink(path)
                        except OSError:
                            pass

        threading.Thread(target=_work, daemon=True).start()

    def _on_automaster_done(self, mastered: np.ndarray, sr: int):
        self._progress.stop()
        self._progress.pack_forget()
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(
            text="✅ Auto-master aplicado", text_color="#4ade80"
        )
        self._player.set_after(mastered)
        self._update_analysis(self.session.get("processed_audio"), mastered, sr)

    def _on_automaster_error(self, error: str):
        self._progress.stop()
        self._progress.pack_forget()
        self._automaster_btn.configure(state="normal", text="⚡ Aplicar Auto-Master")
        self._status_label.configure(text=f"Error: {error}", text_color="#ef4444")

    def _update_analysis(
        self, before: np.ndarray | None, after: np.ndarray | None, sr: int
    ):
        """
        Calcula las métricas de análisis en un hilo daemon y actualiza la UI.

        Métricas calculadas:
            LUFS: loudness integrado vía pyloudnorm (norma ITU-R BS.1770).
            True Peak: máximo valor absoluto del array convertido a dBFS.
                       Se colorea en rojo si supera −0.1 dBTP; a ese nivel
                       algunos codecs lossy pueden generar clipping.
            Dinámica: desviación estándar del array × 100. Es una aproximación
                      rápida del rango dinámico; valores más altos indican
                      más contraste entre partes suaves y fuertes.

        Si before o after son None, esas columnas no se actualizan.
        El cálculo corre en un hilo daemon para no bloquear la UI en tracks largos.
        """

        def _metrics(audio):
            lufs = measure_lufs(audio, sr)
            peak = float(np.max(np.abs(audio)))
            peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
            dr = float(audio.std())
            return lufs, peak_db, dr

        def _work():
            before_m = _metrics(before) if before is not None else None
            after_m = _metrics(after) if after is not None else None

            def _apply():
                if before_m is not None:
                    lufs, peak_db, dr = before_m
                    self._analysis_before["lufs"].configure(text=f"{lufs:.1f} LUFS")
                    self._analysis_before["peak"].configure(text=f"{peak_db:.1f} dBTP")
                    self._analysis_before["dr"].configure(text=f"{dr * 100:.1f} DR")

                if after_m is not None:
                    lufs, peak_db, dr = after_m
                    self._analysis_after["lufs"].configure(text=f"{lufs:.1f} LUFS")
                    self._analysis_after["peak"].configure(
                        text=f"{peak_db:.1f} dBTP",
                        text_color="#4ade80" if peak_db < -0.1 else "#ef4444",
                    )
                    self._analysis_after["dr"].configure(text=f"{dr * 100:.1f} DR")

            self.after(0, _apply)

        threading.Thread(target=_work, daemon=True).start()

    def _export(self):
        """
        Abre el diálogo de guardado y escribe el audio al disco con soundfile.

        Prioridad de fuente: mastered_audio → processed_audio. Si ninguno existe,
        no hace nada (el botón debería estar visible solo cuando hay audio).

        soundfile espera (samples, channels), por lo que el array interno
        (channels, samples) se transpone antes de escribir. WAV usa subtype
        "PCM_24" para 24-bit; FLAC usa la profundidad por defecto de soundfile.
        """
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
        try:
            sf.write(path, audio.T, sr, subtype=subtype)
            filename = os.path.basename(path)
            self._status_label.configure(
                text=f"💾 Guardado: {filename}", text_color="#4ade80"
            )
        except Exception as e:
            self._status_label.configure(
                text=f"Error al guardar: {e}", text_color="#ef4444"
            )
