from pathlib import Path

import pytest

from guimauve.workspace import DataWorkspace

# --- path derivation (pure, no filesystem) ---


def test_dataset_dir():
    ws = DataWorkspace(Path(".guimauve"))
    assert ws.dataset_dir("app_1") == Path(".guimauve/app_1")


def test_data_file_path():
    ws = DataWorkspace(Path(".guimauve"))
    assert ws.data_file("app_1") == Path(".guimauve/app_1/data.yml")


def test_images_and_replays_dir():
    ws = DataWorkspace(Path(".guimauve"))
    assert ws.images_dir("app_1") == Path(".guimauve/app_1/images")
    assert ws.replays_dir("app_1") == Path(".guimauve/app_1/replays")


def test_image_path_is_lowercased():
    ws = DataWorkspace(Path(".guimauve"))
    # element/variant names come UPPER, but the file tree is lowercase
    assert ws.image_path("app_1", "LOGIN", "DEFAULT") == Path(".guimauve/app_1/images/login/default.png")


def test_replay_path_is_lowercased():
    ws = DataWorkspace(Path(".guimauve"))
    assert ws.replay_path("app_1", "MY_REPLAY") == Path(".guimauve/app_1/replays/my_replay.json")


def test_paths_are_relative_to_given_root():
    ws = DataWorkspace(Path("custom_root"))
    assert ws.data_file("app_1") == Path("custom_root/app_1/data.yml")


# --- lifecycle (I/O, tmp_path) ---


@pytest.fixture
def ws(tmp_path):
    return DataWorkspace(tmp_path / ".guimauve")


def test_exists_is_false_when_absent(ws):
    assert ws.exists("app_1") is False


def test_datasets_empty_when_no_root(ws):
    # .guimauve/ itself does not exist yet
    assert ws.datasets() == []


def test_create_dataset_makes_full_layout(ws):
    ws.create_dataset("app_1")
    assert ws.exists("app_1") is True
    assert ws.images_dir("app_1").is_dir()
    assert ws.replays_dir("app_1").is_dir()
    assert ws.data_file("app_1").is_file()


def test_create_dataset_bootstraps_root(ws):
    # .guimauve/ must be created if missing
    assert not ws.root.exists()
    ws.create_dataset("app_1")
    assert ws.root.is_dir()


def test_create_dataset_is_idempotent(ws):
    ws.create_dataset("app_1")
    ws.data_file("app_1").write_text("elements:\n")  # put content
    ws.create_dataset("app_1")  # again -> must not raise nor wipe
    assert ws.data_file("app_1").read_text() == "elements:\n"


def test_datasets_lists_created_ones(ws):
    ws.create_dataset("app_1")
    ws.create_dataset("app_2")
    assert ws.datasets() == ["app_1", "app_2"]  # sorted


def test_datasets_ignores_files_at_root(ws):
    ws.create_dataset("app_1")
    (ws.root / "stray.txt").write_text("x")  # a file, not a dataset dir
    assert ws.datasets() == ["app_1"]


def test_remove_dataset_deletes_the_folder(ws):
    ws.create_dataset("app_1")
    ws.remove_dataset("app_1")
    assert ws.exists("app_1") is False


def test_remove_dataset_leaves_siblings(ws):
    ws.create_dataset("app_1")
    ws.create_dataset("app_2")
    ws.remove_dataset("app_1")
    assert ws.datasets() == ["app_2"]
