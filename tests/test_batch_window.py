import pytest
from ui.batch_window import _remastered_path, BatchItem


def test_remastered_path_wav():
    assert _remastered_path("/music/track_a.wav") == "/music/track_a_remastered.wav"


def test_remastered_path_flac():
    assert _remastered_path("/music/track_b.flac") == "/music/track_b_remastered.wav"


def test_remastered_path_mp3():
    assert _remastered_path("/some/folder/my track.mp3") == "/some/folder/my track_remastered.wav"


def test_batch_item_defaults():
    item = BatchItem(path="/music/a.wav")
    assert item.status == "pending"
    assert item.message == ""
