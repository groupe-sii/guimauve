from pathlib import Path

import pytest

from guimauve.enums import Key
from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.input_event import InputEvent
from guimauve.models.model import ModelError
from guimauve.models.replay import Replay
from guimauve.models.variant import ImageVariant
from guimauve.storage.save import save_replay
from guimauve.storage.sync import (
    _remove_orphaned_images,
    _remove_orphaned_replays,
    _render_entries,
    _render_module,
    sync_all,
    sync_dataset,
)


@pytest.fixture
def pkg_root(tmp_path, monkeypatch):
    """Redirect generated modules out of the installed package into tmp."""
    root = tmp_path / "pkg"
    monkeypatch.setattr("guimauve.storage.sync.files", lambda _pkg: root)
    return root


def _replay(name="RUN_1"):
    return Replay(name=name, events=[InputEvent(t=0.0, action="key_down", args=[Key.A])])


# --- _remove_orphaned_replays ---


def test_remove_orphaned_replays_deletes_unreferenced(workspace):
    kept = workspace.replay_path("app", "RUN_1")
    kept.write_text("[]")
    orphan = workspace.replays_dir("app") / "orphan.json"
    orphan.write_text("[]")

    data = Data(replays={"RUN_1": Replay(name="RUN_1", path=kept)})
    _remove_orphaned_replays(workspace, "app", data)

    assert kept.is_file()  # referenced -> kept
    assert not orphan.exists()  # unreferenced -> removed


def test_remove_orphaned_replays_removes_all_when_none_referenced(workspace):
    orphan = workspace.replay_path("app", "RUN_1")
    orphan.write_text("[]")

    _remove_orphaned_replays(workspace, "app", Data())

    assert not orphan.exists()
    assert workspace.replays_dir("app").is_dir()  # flat files: dir left in place


def test_remove_orphaned_replays_handles_missing_dir(workspace):
    # alias never created -> replays dir does not exist, must not raise
    _remove_orphaned_replays(workspace, "ghost", Data())


# --- _remove_orphaned_images ---


def test_remove_orphaned_images_deletes_unreferenced(workspace):
    kept = workspace.image_path("app", "LOGIN", "DEFAULT")
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_bytes(b"")
    orphan = workspace.image_path("app", "LOGIN", "OLD")
    orphan.write_bytes(b"")

    data = Data(elements={"LOGIN": Element(name="LOGIN", variants={"DEFAULT": ImageVariant(path=kept)})})
    _remove_orphaned_images(workspace, "app", data)

    assert kept.is_file()
    assert not orphan.exists()


def test_remove_orphaned_images_removes_emptied_dirs(workspace):
    orphan = workspace.image_path("app", "OLD", "X")
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"")

    _remove_orphaned_images(workspace, "app", Data())

    assert not orphan.parent.exists()  # emptied element dir is cleaned up (images only)


# --- _render_entries ---


def test_render_entries_empty_returns_pass():
    assert _render_entries({}, "Element") == "    pass"


def test_render_entries_emits_from_dict_line():
    out = _render_entries({"LOGIN": Element(name="LOGIN", x=5)}, "Element")
    assert out.startswith("    LOGIN = Element.from_dict(")


def test_render_entries_rejects_invalid_identifier():
    with pytest.raises(ValueError):
        _render_entries({"class": Element(x=5)}, "Element")  # Python keyword


# --- _render_module ---


def test_render_module_contains_alias_and_both_classes():
    src = _render_module(Data(), "app")
    assert "ALIAS = 'app'" in src
    assert "class Elements(" in src
    assert "class Replays(" in src
    assert "    pass" in src  # empty bodies


def test_render_module_is_valid_python():
    data = Data(
        elements={"LOGIN": Element(name="LOGIN", x=5)},
        replays={"RUN_1": Replay(name="RUN_1", path=Path("replays/run_1.json"))},
    )
    src = _render_module(data, "app")
    compile(src, "<generated>", "exec")  # must be syntactically valid


# --- sync_dataset ---


def test_sync_dataset_writes_module_for_valid_data(workspace, pkg_root):
    save_replay(workspace, "app", _replay())

    error = sync_dataset(workspace, "app")

    assert error is None
    module = pkg_root / "data" / "app.py"
    assert module.is_file()
    assert "class Replays(" in module.read_text()


def test_sync_dataset_returns_error_for_invalid_data(workspace, pkg_root):
    # a replay pointing at a missing file -> resolve() fails
    workspace.data_file("app").write_text("replays:\n  RUN_1:\n    name: RUN_1\n    path: replays/missing.json\n")

    error = sync_dataset(workspace, "app")

    assert isinstance(error, ModelError)


def test_sync_dataset_removes_orphaned_replays(workspace, pkg_root):
    save_replay(workspace, "app", _replay())
    orphan = workspace.replays_dir("app") / "orphan.json"
    orphan.write_text("[]")

    sync_dataset(workspace, "app")

    assert not orphan.exists()


# --- sync_all ---


def test_sync_all_prunes_stale_modules(workspace, pkg_root):
    save_replay(workspace, "app", _replay())
    data_dir = pkg_root / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "ghost.py").write_text("# stale: no such dataset")
    (data_dir / "__init__.py").write_text("")

    failures = sync_all(workspace)

    assert failures == {}
    assert (data_dir / "app.py").is_file()  # (re)generated
    assert not (data_dir / "ghost.py").exists()  # pruned
    assert (data_dir / "__init__.py").is_file()  # kept
