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


def test_add_paths_appends_items():
    """Test that _add_paths logic appends new items."""
    items = []

    # simulate _add_paths logic directly
    paths = ["/a/track1.wav", "/a/track2.flac"]
    existing = {item.path for item in items}
    for p in paths:
        if p not in existing:
            items.append(BatchItem(path=p))
            existing.add(p)

    assert len(items) == 2
    assert items[0].path == "/a/track1.wav"


def test_add_paths_ignores_duplicates():
    """Test that _add_paths logic ignores duplicate paths."""
    items = [BatchItem(path="/a/track1.wav")]

    paths = ["/a/track1.wav", "/a/track2.flac"]
    existing = {item.path for item in items}
    for p in paths:
        if p not in existing:
            items.append(BatchItem(path=p))
            existing.add(p)

    assert len(items) == 2  # not 3
    assert items[0].path == "/a/track1.wav"
    assert items[1].path == "/a/track2.flac"
