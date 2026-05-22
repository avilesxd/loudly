import numpy as np
from pedalboard import HighShelfFilter, LowShelfFilter, PeakFilter, Pedalboard


def apply_eq(
    audio: np.ndarray,
    sample_rate: int,
    low_gain: float = 0.0,  # 80 Hz shelf
    low_mid_gain: float = 0.0,  # 250 Hz peak
    hi_mid_gain: float = 0.0,  # 2500 Hz peak
    high_gain: float = 0.0,  # 8000 Hz shelf
) -> np.ndarray:
    """
    Aplica un ecualizador de 4 bandas al audio usando filtros de Pedalboard.

    Configuración de bandas:
        - Low (80 Hz): LowShelfFilter — controla el peso general del bajo.
        - Low-Mid (250 Hz): PeakFilter — zona de calidez o barro de la mezcla.
        - Hi-Mid (2.5 kHz): PeakFilter — presencia y ataque de voces e instrumentos.
        - High (8 kHz): HighShelfFilter — aire y brillo en los agudos.

    Si todos los gains son 0.0, devuelve una copia sin pasar por Pedalboard
    para evitar la latencia de inicializar el grafo de DSP.

    Args:
        audio: Array float32 (channels, samples).
        sample_rate: Frecuencia de muestreo en Hz.
        low_gain: Ganancia del shelf a 80 Hz, en dB. Rango típico: −12 a +12.
        low_mid_gain: Ganancia del pico a 250 Hz, en dB.
        hi_mid_gain: Ganancia del pico a 2.5 kHz, en dB.
        high_gain: Ganancia del shelf a 8 kHz, en dB.

    Returns:
        Array float32 (channels, samples) con la EQ aplicada.
    """
    if all(g == 0.0 for g in [low_gain, low_mid_gain, hi_mid_gain, high_gain]):
        return audio.copy()

    board = Pedalboard(
        [
            LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=low_gain, q=0.707),
            PeakFilter(cutoff_frequency_hz=250.0, gain_db=low_mid_gain, q=1.0),
            PeakFilter(cutoff_frequency_hz=2500.0, gain_db=hi_mid_gain, q=1.0),
            HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=high_gain, q=0.707),
        ]
    )
    return board(audio, sample_rate)
