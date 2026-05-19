import customtkinter as ctk
from tkinter import filedialog
from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


class Step1Load(ctk.CTkFrame):
    def __init__(self, parent, session: dict, on_next):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.session = session
        self.on_next = on_next

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Carga tu track para masterizar",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(40, 6))
        ctk.CTkLabel(
            self, text="Formatos: WAV · MP3 · FLAC · AIFF",
            text_color="#888888"
        ).pack(pady=(0, 20))

        # Main track
        track_frame = ctk.CTkFrame(self, width=500, height=100, corner_radius=12)
        track_frame.pack(pady=8)
        track_frame.pack_propagate(False)

        self._track_label = ctk.CTkLabel(
            track_frame, text="📁  Sin archivo seleccionado",
            text_color="#666666", font=ctk.CTkFont(size=13)
        )
        self._track_label.pack(expand=True)
        ctk.CTkButton(
            track_frame, text="Seleccionar track principal",
            command=self._pick_track, width=220
        ).pack(pady=(0, 12))

        # Reference track (optional)
        ref_frame = ctk.CTkFrame(self, width=500, height=80, corner_radius=12,
                                  border_width=1, border_color="#333333")
        ref_frame.pack(pady=8)
        ref_frame.pack_propagate(False)

        self._ref_label = ctk.CTkLabel(
            ref_frame, text="🎯  Referencia: no seleccionada  (opcional)",
            text_color="#555555", font=ctk.CTkFont(size=12)
        )
        self._ref_label.pack(expand=True)
        ctk.CTkButton(
            ref_frame, text="Seleccionar referencia",
            command=self._pick_reference, width=200,
            fg_color="#1e1e2e", hover_color="#2d2d3e"
        ).pack(pady=(0, 8))

        self._error_label = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self._error_label.pack(pady=4)

        self._next_btn = ctk.CTkButton(
            self, text="Siguiente →", command=self._advance,
            state="disabled", width=140
        )
        self._next_btn.pack(pady=20)

    def _pick_track(self):
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return
        try:
            audio, sr = load_audio(path)
            self.session["audio_path"] = path
            self.session["audio_data"] = audio
            self.session["sample_rate"] = sr
            self.session["processed_audio"] = audio.copy()
            name = path.split("/")[-1].split("\\")[-1]
            self._track_label.configure(
                text=f"✅  {name}  ({sr} Hz, {audio.shape[0]}ch)",
                text_color="#4ade80"
            )
            self._error_label.configure(text="")
            self._next_btn.configure(state="normal")
        except Exception as e:
            self._error_label.configure(text=f"Error: {e}")

    def _pick_reference(self):
        path = filedialog.askopenfilename(filetypes=SUPPORTED)
        if not path:
            return
        self.session["reference_path"] = path
        name = path.split("/")[-1].split("\\")[-1]
        self._ref_label.configure(
            text=f"✅  Referencia: {name}", text_color="#60a5fa"
        )

    def _advance(self):
        if self.session.get("audio_data") is not None:
            self.on_next()

    def on_enter(self):
        pass
