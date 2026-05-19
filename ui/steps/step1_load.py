import os
import threading
from tkinter import filedialog

import customtkinter as ctk

from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


class Step1Load(ctk.CTkFrame):
    """
    Paso 1 del wizard: selección del track principal y del track de referencia.

    El track principal se decodifica en un hilo daemon para no bloquear la UI
    durante la carga de archivos grandes. El processed_audio se inicializa como
    copia del audio original para que el paso 2 tenga algo que mostrar incluso
    si el usuario no toca los sliders.

    El track de referencia no se decodifica en este paso — matchering lo lee
    directamente desde disco en el paso 3, por eso solo se guarda la ruta.
    """

    def __init__(self, parent, session: dict, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_next = on_next

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Carga tu track para masterizar",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(40, 6))
        ctk.CTkLabel(
            self, text="Formatos: WAV · MP3 · FLAC · AIFF", text_color="#888888"
        ).pack(pady=(0, 20))

        # Main track
        track_frame = ctk.CTkFrame(self, width=500, height=100, corner_radius=12)
        track_frame.pack(pady=8)
        track_frame.pack_propagate(False)

        self._track_label = ctk.CTkLabel(
            track_frame,
            text="📁  Sin archivo seleccionado",
            text_color="#666666",
            font=ctk.CTkFont(size=13),
        )
        self._track_label.pack(expand=True)
        self._pick_btn = ctk.CTkButton(
            track_frame,
            text="Seleccionar track principal",
            command=self._pick_track,
            width=220,
        )
        self._pick_btn.pack(pady=(0, 12))

        # Reference track (optional)
        ref_frame = ctk.CTkFrame(
            self,
            width=500,
            height=80,
            corner_radius=12,
            border_width=1,
            border_color="#333333",
        )
        ref_frame.pack(pady=8)
        ref_frame.pack_propagate(False)

        self._ref_label = ctk.CTkLabel(
            ref_frame,
            text="🎯  Referencia: no seleccionada  (opcional)",
            text_color="#555555",
            font=ctk.CTkFont(size=12),
        )
        self._ref_label.pack(expand=True)
        ctk.CTkButton(
            ref_frame,
            text="Seleccionar referencia",
            command=self._pick_reference,
            width=200,
            fg_color="#1e1e2e",
            hover_color="#2d2d3e",
        ).pack(pady=(0, 8))

        self._error_label = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self._error_label.pack(pady=4)

        self._next_btn = ctk.CTkButton(
            self, text="Siguiente →", command=self._advance, state="disabled", width=140
        )
        self._next_btn.pack(pady=20)

    def _pick_track(self):
        """
        Abre el diálogo de selección, luego decodifica el archivo en un hilo daemon.

        El diálogo debe ejecutarse en el hilo principal (Tkinter). Solo la
        decodificación con load_audio se corre en el hilo, para no bloquear la UI
        con archivos grandes. El botón se deshabilita durante la carga para evitar
        lanzar múltiples hilos simultáneos.
        """
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return

        self._pick_btn.configure(state="disabled")
        self._next_btn.configure(state="disabled")
        self._track_label.configure(text="⏳  Cargando…", text_color="#888888")
        self._error_label.configure(text="")

        def _work():
            try:
                audio, sr = load_audio(path)

                def _on_success():
                    self.session.update(
                        {
                            "audio_path": path,
                            "audio_data": audio,
                            "sample_rate": sr,
                            "processed_audio": audio.copy(),
                            "mastered_audio": None,
                        }
                    )
                    name = os.path.basename(path)
                    self._track_label.configure(
                        text=f"✅  {name}  ({sr} Hz, {audio.shape[0]}ch)",
                        text_color="#4ade80",
                    )
                    self._pick_btn.configure(state="normal")
                    self._next_btn.configure(state="normal")

                self.after(0, _on_success)
            except Exception as e:

                def _on_error(err=str(e)):
                    self._error_label.configure(text=f"Error: {err}")
                    self._pick_btn.configure(state="normal")

                self.after(0, _on_error)

        threading.Thread(target=_work, daemon=True).start()

    def _pick_reference(self):
        """
        Registra la ruta del track de referencia en session sin decodificarlo.

        La decodificación la hace matchering internamente en el paso 3.
        No se valida el formato aquí; matchering reportará el error al procesar.
        """
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return
        self.session["reference_path"] = path
        name = os.path.basename(path)
        self._ref_label.configure(text=f"✅  Referencia: {name}", text_color="#60a5fa")

    def _advance(self):
        if self.session.get("audio_data") is not None:
            self.on_next()

    def on_enter(self):
        pass
