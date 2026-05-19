# audio/limiter.py
import numpy as np
import pyloudnorm as pyln


def measure_lufs(audio: np.ndarray, sample_rate: int) -> float:
    """
    Mide el LUFS integrado del audio.
    audio: (channels, samples) float32
    """
    meter = pyln.Meter(sample_rate)
    # pyloudnorm expects (samples, channels)
    loudness = meter.integrated_loudness(audio.T.astype(np.float64))
    return float(loudness)


def apply_limiter(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -14.0,
) -> np.ndarray:
    """
    Normaliza al LUFS objetivo y aplica true-peak limiter a -0.3 dBTP.
    audio: (channels, samples) float32
    Retorna: (channels, samples) float32
    """
    current_lufs = measure_lufs(audio, sample_rate)

    # Normalize with pyloudnorm (works in float64, (samples, channels))
    meter = pyln.Meter(sample_rate)
    normalized = pyln.normalize.loudness(
        audio.T.astype(np.float64), current_lufs, target_lufs
    )
    normalized = normalized.T.astype(np.float32)  # back to (channels, samples)

    # True-peak limiter at -0.3 dBFS to prevent clipping on format conversion.
    # Pedalboard's Limiter applies makeup gain (brings signal up to threshold),
    # so we use numpy clip which only attenuates, never boosts.
    threshold_linear = float(10 ** (-0.3 / 20))  # -0.3 dBFS ≈ 0.9661
    limited = np.clip(normalized, -threshold_linear, threshold_linear)
    return limited
