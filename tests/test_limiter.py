import numpy as np

from audio.limiter import apply_limiter, measure_lufs


def test_measure_lufs_returns_float(sine_wav):
    path, audio, sr = sine_wav
    lufs = measure_lufs(audio, sr)
    assert isinstance(lufs, float)
    assert -60.0 < lufs < 0.0


def test_apply_limiter_reaches_target_lufs(sine_wav):
    path, audio, sr = sine_wav
    target = -14.0
    result = apply_limiter(audio, sr, target_lufs=target)
    measured = measure_lufs(result, sr)
    assert abs(measured - target) < 0.5  # tolerance 0.5 LUFS


def test_apply_limiter_no_clipping(sine_wav):
    path, audio, sr = sine_wav
    result = apply_limiter(audio, sr, target_lufs=-14.0)
    assert result.max() <= 1.0
    assert result.min() >= -1.0


def test_apply_limiter_output_shape_matches_input(sine_wav):
    path, audio, sr = sine_wav
    result = apply_limiter(audio, sr, target_lufs=-14.0)
    assert result.shape == audio.shape
    assert result.dtype == np.float32
