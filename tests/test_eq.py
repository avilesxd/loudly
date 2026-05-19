import numpy as np

from audio.eq import apply_eq


def test_eq_with_zero_gains_is_passthrough(sine_wav):
    path, original_audio, sr = sine_wav
    result = apply_eq(original_audio, sr, 0.0, 0.0, 0.0, 0.0)
    assert result.shape == original_audio.shape
    assert result.dtype == np.float32
    np.testing.assert_allclose(result, original_audio, atol=1e-4)


def test_eq_positive_gain_increases_rms(sine_wav):
    path, audio, sr = sine_wav
    boosted = apply_eq(
        audio, sr, low_gain=6.0, low_mid_gain=0.0, hi_mid_gain=0.0, high_gain=0.0
    )
    assert boosted.std() > audio.std()


def test_eq_negative_gain_decreases_rms(sine_wav):
    path, audio, sr = sine_wav
    cut = apply_eq(
        audio, sr, low_gain=-6.0, low_mid_gain=0.0, hi_mid_gain=0.0, high_gain=0.0
    )
    assert cut.std() < audio.std()


def test_eq_output_shape_matches_input(sine_wav):
    path, audio, sr = sine_wav
    result = apply_eq(audio, sr, 3.0, -2.0, 1.5, -1.0)
    assert result.shape == audio.shape
