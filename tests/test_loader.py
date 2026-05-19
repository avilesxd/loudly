import numpy as np
import pytest
from audio.loader import load_audio

def test_load_wav_returns_float32_channels_first(sine_wav):
    path, original_audio, sr = sine_wav
    audio, sample_rate = load_audio(path)
    assert audio.dtype == np.float32
    assert audio.ndim == 2
    assert audio.shape[0] <= 2          # channels first, max 2 (stereo)
    assert audio.shape[1] > 0           # has samples
    assert sample_rate == 44100

def test_load_audio_values_in_range(sine_wav):
    path, _, _ = sine_wav
    audio, _ = load_audio(path)
    assert audio.max() <= 1.0
    assert audio.min() >= -1.0

def test_load_unsupported_format_raises(tmp_path):
    bad_file = tmp_path / "file.xyz"
    bad_file.write_bytes(b"not audio")
    with pytest.raises(ValueError, match="Formato no soportado"):
        load_audio(str(bad_file))
