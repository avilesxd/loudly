import numpy as np
import soundfile as sf
import tempfile
import os

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".aiff", ".aif"}
MINIAUDIO_EXTENSIONS = {".mp3"}

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """
    Lee un archivo de audio y lo devuelve normalizado como array float32.

    Soporta WAV, FLAC y AIFF vía soundfile, y MP3 vía miniaudio (soundfile
    no incluye decodificación MP3 en Python 3.13). El array resultante siempre
    tiene forma (channels, samples) independientemente del formato de origen.

    Args:
        path: Ruta al archivo de audio.

    Returns:
        Tupla (audio, sample_rate) donde audio es float32 (channels, samples).

    Raises:
        ValueError: Si la extensión del archivo no está entre las soportadas.
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
    """
    Decodifica un MP3 usando miniaudio y lo convierte a (channels, samples) float32.

    miniaudio devuelve las muestras intercaladas (L, R, L, R…) en un buffer
    contiguo; hay que reshape a (samples, channels) antes de transponer.
    """
    import miniaudio
    decoded = miniaudio.mp3_read_file_f32(path)
    audio = np.frombuffer(decoded.samples, dtype=np.float32)
    # miniaudio returns interleaved samples → reshape to (samples, channels)
    audio = audio.reshape(-1, decoded.nchannels).T  # → (channels, samples)
    return audio, decoded.sample_rate
