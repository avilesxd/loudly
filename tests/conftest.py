import numpy as np
import soundfile as sf
import pytest
import tempfile
import os

@pytest.fixture
def sine_wav(tmp_path):
    """Genera un archivo WAV de 3 segundos con un tono de 440 Hz a -18 LUFS aprox."""
    sample_rate = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.float32)
    audio = np.stack([signal, signal])  # (2, samples)
    path = str(tmp_path / "test_sine.wav")
    sf.write(path, audio.T, sample_rate, subtype="FLOAT")
    return path, audio, sample_rate
