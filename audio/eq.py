# audio/eq.py
import numpy as np
from pedalboard import Pedalboard, LowShelfFilter, HighShelfFilter, PeakFilter

def apply_eq(
    audio: np.ndarray,
    sample_rate: int,
    low_gain: float = 0.0,      # 80 Hz shelf
    low_mid_gain: float = 0.0,  # 250 Hz peak
    hi_mid_gain: float = 0.0,   # 2500 Hz peak
    high_gain: float = 0.0,     # 8000 Hz shelf
) -> np.ndarray:
    """
    Aplica EQ de 4 bandas.
    audio: (channels, samples) float32
    Retorna: (channels, samples) float32
    """
    if all(g == 0.0 for g in [low_gain, low_mid_gain, hi_mid_gain, high_gain]):
        return audio.copy()

    board = Pedalboard([
        LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=low_gain, q=0.707),
        PeakFilter(cutoff_frequency_hz=250.0, gain_db=low_mid_gain, q=1.0),
        PeakFilter(cutoff_frequency_hz=2500.0, gain_db=hi_mid_gain, q=1.0),
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=high_gain, q=0.707),
    ])
    return board(audio, sample_rate)
