# audio/loader.py
import numpy as np
import soundfile as sf
import tempfile
import os

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".aiff", ".aif"}
MINIAUDIO_EXTENSIONS = {".mp3"}

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """
    Carga un archivo de audio y retorna (audio, sample_rate).
    audio shape: (channels, samples), dtype float32.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in MINIAUDIO_EXTENSIONS:
        return _load_mp3(path)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {ext}")

    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    # soundfile → (samples, channels); transpose to (channels, samples)
    audio = data.T
    return audio, sample_rate

def _load_mp3(path: str) -> tuple[np.ndarray, int]:
    """Loads MP3 via miniaudio (Python 3.13 compatible)."""
    import miniaudio
    decoded = miniaudio.mp3_read_file_f32(path)
    audio = np.frombuffer(decoded.samples, dtype=np.float32)
    # miniaudio returns interleaved samples → reshape to (samples, channels)
    audio = audio.reshape(-1, decoded.nchannels).T  # → (channels, samples)
    return audio, decoded.sample_rate
