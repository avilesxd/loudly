import os

import numpy as np
import pytest
import soundfile as sf

from audio.automaster import apply_automaster


@pytest.fixture
def two_wav_files(tmp_path):
    """Generates target and reference as WAV files."""
    sr = 44100
    t = np.linspace(0, 3.0, int(sr * 3.0), endpoint=False).astype(np.float32)
    target_audio = np.stack([np.sin(2 * np.pi * 440 * t) * 0.1] * 2)
    ref_audio = np.stack([np.sin(2 * np.pi * 880 * t) * 0.2] * 2)

    target_path = str(tmp_path / "target.wav")
    ref_path = str(tmp_path / "reference.wav")
    out_path = str(tmp_path / "output.wav")

    sf.write(target_path, target_audio.T, sr, subtype="PCM_24")
    sf.write(ref_path, ref_audio.T, sr, subtype="PCM_24")
    return target_path, ref_path, out_path


def test_apply_automaster_creates_output_file(two_wav_files):
    target, reference, output = two_wav_files
    apply_automaster(target, reference, output)
    assert os.path.exists(output)
    assert os.path.getsize(output) > 0


def test_apply_automaster_output_is_valid_wav(two_wav_files):
    target, reference, output = two_wav_files
    apply_automaster(target, reference, output)
    data, sr = sf.read(output)
    assert data.ndim == 2  # stereo
    assert sr > 0
