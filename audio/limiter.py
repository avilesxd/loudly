import numpy as np
import pyloudnorm as pyln


def measure_lufs(audio: np.ndarray, sample_rate: int) -> float:
    """
    Calcula el loudness integrado del audio según la norma ITU-R BS.1770.

    pyloudnorm espera (samples, channels) en float64, por lo que se transpone
    y convierte antes de pasarlo al medidor.

    Args:
        audio: Array float32 (channels, samples).
        sample_rate: Frecuencia de muestreo en Hz.

    Returns:
        Loudness integrado en LUFS. Devuelve -inf si el audio es silencio.
    """
    meter = pyln.Meter(sample_rate)
    loudness = meter.integrated_loudness(audio.T.astype(np.float64))
    return float(loudness)


def apply_limiter(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -14.0,
) -> np.ndarray:
    """
    Normaliza el audio al loudness objetivo y aplica un true-peak limiter.

    Proceso en dos etapas:
      1. Normalización LUFS: pyloudnorm calcula el gain necesario para alcanzar
         target_lufs y lo aplica de forma lineal sobre toda la señal.
      2. True-peak limiting: np.clip recorta a ±0.9661 (−0.3 dBFS). Se usa clip
         en lugar del Limiter de Pedalboard porque Pedalboard aplica makeup gain
         (puede amplificar hasta el umbral), mientras que clip solo atenúa.

    Args:
        audio: Array float32 (channels, samples).
        sample_rate: Frecuencia de muestreo en Hz.
        target_lufs: Loudness objetivo en LUFS (−14 Spotify, −13 YouTube, −9 CD).

    Returns:
        Array float32 (channels, samples) normalizado y con el pico recortado
        a −0.3 dBFS.
    """
    current_lufs = measure_lufs(audio, sample_rate)
    if not np.isfinite(current_lufs):
        raise ValueError("El audio es silencio o demasiado débil para normalizar.")

    normalized = pyln.normalize.loudness(
        audio.T.astype(np.float64), current_lufs, target_lufs
    )
    normalized = normalized.T.astype(np.float32)

    threshold_linear = float(10 ** (-0.3 / 20))  # -0.3 dBFS ≈ 0.9661
    limited = np.clip(normalized, -threshold_linear, threshold_linear)
    return limited
