import sys
from pathlib import Path

import customtkinter as ctk

from ui.steps.step1_load import Step1Load
from ui.steps.step2_edit import Step2Edit
from ui.steps.step3_master import Step3Master


def _resource(relative: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return str(base / relative)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LoudlyApp(ctk.CTk):
    """
    Ventana principal de Loudly. Implementa un wizard de 3 pasos.

    El estado de la sesión vive en self.session, un diccionario que se pasa
    por referencia a los tres pasos. Cada paso puede leerlo y modificarlo
    directamente; no hay callbacks de estado entre pasos.

    Claves del session:
        audio_path (str | None): ruta al track principal cargado.
        reference_path (str | None): ruta al track de referencia (opcional).
        audio_data (ndarray | None): audio original, float32 (channels, samples).
        sample_rate (int | None): frecuencia de muestreo del track principal.
        processed_audio (ndarray | None): audio tras aplicar EQ y limiter en el paso 2.
        mastered_audio (ndarray | None): audio tras aplicar matchering en el paso 3.
        eq_params (dict): ganancias de EQ en dB — claves: low, low_mid, hi_mid, high.
        lufs_target (float): loudness objetivo para el limitador, en LUFS.
    """

    def __init__(self):
        super().__init__()
        self.title("Loudly — Masterizador")
        self.geometry("900x620")
        self.resizable(False, False)
        self.iconbitmap(_resource("assets/loudly.ico"))

        self.session: dict = {
            "audio_path": None,
            "reference_path": None,
            "audio_data": None,
            "sample_rate": None,
            "processed_audio": None,
            "mastered_audio": None,
            "eq_params": {"low": 0.0, "low_mid": 0.0, "hi_mid": 0.0, "high": 0.0},
            "lufs_target": -14.0,
        }

        self._steps: list[ctk.CTkFrame] = []
        self._current_step = 0

        self._build_header()
        self._build_steps()
        self._show_step(0)

    def _build_header(self):
        header = ctk.CTkFrame(self, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🎵  LOUDLY", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=20)

        self._step_labels = []
        steps_frame = ctk.CTkFrame(header, fg_color="transparent")
        steps_frame.pack(side="right", padx=20)

        for name in ["① Cargar", "② Ajustar", "③ Masterizar"]:
            lbl = ctk.CTkLabel(steps_frame, text=name, font=ctk.CTkFont(size=12))
            lbl.pack(side="left", padx=10)
            self._step_labels.append(lbl)

    def _build_steps(self):
        self._container = ctk.CTkFrame(self, corner_radius=0)
        self._container.pack(fill="both", expand=True)

        self._steps = [
            Step1Load(
                self._container, self.session, on_next=lambda: self._show_step(1)
            ),
            Step2Edit(
                self._container,
                self.session,
                on_back=lambda: self._show_step(0),
                on_next=lambda: self._show_step(2),
            ),
            Step3Master(
                self._container, self.session, on_back=lambda: self._show_step(1)
            ),
        ]

    def _show_step(self, index: int):
        """
        Oculta el paso actual, coloca el nuevo y llama a su on_enter().

        on_enter() permite a cada paso inicializarse con el session actualizado
        (por ejemplo, Step2Edit renderiza la waveform al entrar al paso 2,
        y Step3Master actualiza el análisis si el usuario vuelve del paso 2).
        """
        self._steps[self._current_step].place_forget()
        self._current_step = index
        self._steps[index].place(relwidth=1, relheight=1)
        self._steps[index].on_enter()
        self._update_step_labels(index)

    def _update_step_labels(self, active: int):
        for i, lbl in enumerate(self._step_labels):
            color = "#7C3AED" if i == active else "#555555"
            lbl.configure(text_color=color)
