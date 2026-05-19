# audio/loader.py
import numpy as np
import soundfile as sf
import tempfile
import os

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".aiff", ".aif"}
PYDUB_EXTENSIONS = {".mp3"}

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """
    Carga un archivo de audio y retorna (audio, sample_rate).
    audio shape: (channels, samples), dtype float32.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in PYDUB_EXTENSIONS:
        path = _convert_to_wav(path)
        ext = ".wav"

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {ext}")

    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    # soundfile → (samples, channels); transpose to (channels, samples)
    audio = data.T
    return audio, sample_rate

def _convert_to_wav(path: str) -> str:
    """Converts MP3 to temp WAV and returns the WAV path."""
    from pydub import AudioSegment  # lazy import — pydub requires pyaudioop (not on Py 3.13 stdlib)
    segment = AudioSegment.from_mp3(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    segment.export(tmp.name, format="wav")
    return tmp.name
