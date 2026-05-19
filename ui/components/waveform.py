import numpy as np
import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class WaveformCanvas(ctk.CTkFrame):
    """Shows audio waveform as embedded matplotlib figure."""

    def __init__(self, parent, width=860, height=100, **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self._fig = Figure(figsize=(width / 100, height / 100), dpi=100)
        self._fig.patch.set_facecolor("#0d0d0d")
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def render(self, audio: np.ndarray, color: str = "#7C3AED"):
        """
        Dibuja la forma de onda del audio en el canvas.

        Para mejorar el rendimiento con archivos largos, mezcla todos los canales
        a mono (promedio) y hace downsample a máximo 2000 puntos antes de graficar.
        Dibuja la línea de onda más un área de relleno con transparencia para
        mejorar la legibilidad visual.

        Args:
            audio: Array float32 (channels, samples).
            color: Color hex de la línea y el área de relleno.
        """
        self._ax.clear()
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")

        # Mix to mono and downsample for display
        mono = audio.mean(axis=0)
        downsample = max(1, len(mono) // 2000)
        display = mono[::downsample]

        self._ax.plot(display, color=color, linewidth=0.6, alpha=0.9)
        self._ax.fill_between(range(len(display)), display, alpha=0.3, color=color)
        self._fig.tight_layout(pad=0)
        self._canvas.draw()

    def clear(self):
        self._ax.clear()
        self._ax.set_facecolor("#0d0d0d")
        self._ax.axis("off")
        self._canvas.draw()
