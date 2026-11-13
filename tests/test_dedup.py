import json
from datetime import date

import pytest

from arxiv_radar.dedup import SeenStore


def test_roundtrip(tmp_path):
    path = str(tmp_path / "seen.json")
    store = SeenStore(path)
    assert not store.is_seen("a")
    store.mark(["a", "b"], when=date(2026, 11, 10))
    store.save()

    reloaded = SeenStore(path)
    assert reloaded.is_seen("a")
    assert reloaded.is_seen("b")
    assert not reloaded.is_seen("c")


def test_filter_unseen(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    store.mark(["x"])
    assert store.filter_unseen(["x", "y", "x"]) == ["y"]


def test_mark_does_not_overwrite_first_seen(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    store.mark(["x"], when=date(2026, 1, 1))
    store.mark(["x"], when=date(2026, 11, 11))
    store.save()
    with open(str(tmp_path / "seen.json"), encoding="utf-8") as fh:
        assert json.load(fh)["papers"]["x"] == "2026-01-01"


def test_prune_removes_old_entries(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    store.mark(["old"], when=date(2026, 1, 1))
    store.mark(["new"], when=date.today())
    removed = store.prune(keep_days=30)
    assert removed == 1
    assert not store.is_seen("old")
    assert store.is_seen("new")


@pytest.mark.parametrize(
    "content",
    [b"{ not json !!!", b"\xff", b'{"papers": null}', b'{"papers": []}'],
    ids=["invalid-json", "invalid-utf8", "null-papers", "array-papers"],
)
def test_corrupted_state_is_tolerated(tmp_path, content):
    path = tmp_path / "seen.json"
    path.write_bytes(content)
    store = SeenStore(str(path))
    assert len(store) == 0
    store.mark(["z"])
    store.save()  # repairs the file
    assert SeenStore(str(path)).is_seen("z")


def test_save_is_atomic_and_creates_dirs(tmp_path):
    path = str(tmp_path / "nested" / "dir" / "seen.json")
    store = SeenStore(path)
    store.mark(["k"])
    store.save()
    assert SeenStore(path).is_seen("k")
    leftovers = [f for f in (tmp_path / "nested" / "dir").iterdir() if f.name != "seen.json"]
    assert leftovers == []
