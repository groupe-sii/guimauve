import logging
import platform

import pytest

from guimauve.checks import (
    EnvironmentCheckError,
    check_dataset,
    check_scaling,
    check_screen_exists,
    check_screen_size,
    selected_datasets,
)
from guimauve.drivers.driver import Screen
from guimauve.storage.sync import sync_dataset
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.screen import get_scaling

# ============ EnvironmentCheckError ============


def test_error_keeps_failures():
    failures = ["scaling: expected 100%, got 125%"]
    assert EnvironmentCheckError(failures).failures == failures


def test_error_is_a_runtime_error():
    assert isinstance(EnvironmentCheckError(["x"]), RuntimeError)


def test_message_singular():
    message = str(EnvironmentCheckError(["scaling: expected 100%, got 125%"]))
    assert "(1 failure)" in message
    assert "  - scaling: expected 100%, got 125%" in message


def test_message_lists_every_failure():
    message = str(EnvironmentCheckError(["screen_size: a", "datasets: b"]))
    assert "(2 failures)" in message
    assert "  - screen_size: a" in message
    assert "  - datasets: b" in message


# ============ check_screen_exists ============


SCREENS = [Screen(0, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(1920, 0, 1280, 720)]


@pytest.mark.parametrize("number", [1, 2])
def test_existing_screen_passes(number):
    assert check_screen_exists(number, SCREENS) is None


def test_missing_screen_fails():
    assert check_screen_exists(3, SCREENS) == "screen 3: does not exist, 2 screens available"


def test_missing_screen_message_singular():
    assert check_screen_exists(2, SCREENS[:2]) == "screen 2: does not exist, 1 screen available"


# ============ check_screen_size ============


def test_screen_size_matching_passes():
    assert check_screen_size(1, (1920, 1080), (1920, 1080)) is None


def test_screen_size_mismatch_fails():
    assert check_screen_size(2, (1280, 720), (1920, 1080)) == "screen 2: size expected 1280x720, got 1920x1080"


# ============ check_scaling ============


@pytest.fixture
def windows(monkeypatch):
    """Pretends to run on Windows, with screen 1 scaled at 125% and screen 2 at 100%."""
    monkeypatch.setattr("guimauve.checks.platform.system", lambda: "Windows")
    monkeypatch.setattr("guimauve.checks.get_scaling", lambda screen: {1: 125, 2: 100}[screen])


def test_scaling_matching_passes(windows):
    assert check_scaling(1, 125, "local") is None


def test_scaling_reads_the_requested_screen(windows):
    assert check_scaling(2, 100, "local") is None


def test_scaling_mismatch_fails(windows):
    assert check_scaling(2, 75, "local") == "screen 2: scaling expected 75%, got 100%"


def test_scaling_skipped_in_vnc_mode(windows, caplog):
    with caplog.at_level(logging.WARNING):
        assert check_scaling(1, 100, "vnc") is None
    assert "Scaling check skipped" in caplog.text


def test_scaling_skipped_outside_windows(monkeypatch, caplog):
    monkeypatch.setattr("guimauve.checks.platform.system", lambda: "Linux")
    with caplog.at_level(logging.WARNING):
        assert check_scaling(1, 100, "local") is None
    assert "Scaling check skipped" in caplog.text


def test_scaling_skipped_when_unreadable(windows, monkeypatch, caplog):
    def fail(screen):
        raise OSError("boom")

    monkeypatch.setattr("guimauve.checks.get_scaling", fail)
    with caplog.at_level(logging.WARNING):
        assert check_scaling(1, 100, "local") is None
    assert "cannot read the display scaling" in caplog.text


@pytest.mark.skipif(platform.system() != "Windows", reason="reads the real Windows display scaling")
def test_get_scaling_on_real_windows():
    assert get_scaling(1) >= 100


# ============ datasets ============


@pytest.fixture
def pkg_root(tmp_path, monkeypatch):
    """Redirect generated modules out of the installed package into tmp."""
    root = tmp_path / "pkg"
    monkeypatch.setattr("guimauve.storage.sync.files", lambda _pkg: root)
    return root


@pytest.fixture
def workspace(tmp_path, pkg_root):
    """A workspace with one dataset 'app', synced and up to date."""
    ws = DataWorkspace(tmp_path / ".guimauve")
    ws.create_dataset("app")
    sync_dataset(ws, "app")
    return ws


def _module(pkg_root, alias="app"):
    return pkg_root / "data" / f"{alias}.py"


def test_selected_datasets_false_selects_nothing(workspace):
    assert selected_datasets(workspace, False) == []


def test_selected_datasets_true_selects_every_dataset(workspace):
    workspace.create_dataset("other")
    assert selected_datasets(workspace, True) == ["app", "other"]


def test_selected_datasets_list_is_kept_as_is(workspace):
    assert selected_datasets(workspace, ["app", "nope"]) == ["app", "nope"]


def test_selected_datasets_true_without_dataset_warns(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert selected_datasets(DataWorkspace(tmp_path / "empty"), True) == []
    assert "Dataset check skipped" in caplog.text


def test_up_to_date_dataset_passes(workspace):
    assert check_dataset(workspace, "app") is None


def test_comment_only_change_passes(workspace):
    workspace.data_file("app").write_text("# just a comment\n")
    assert check_dataset(workspace, "app") is None


def test_changed_data_file_fails(workspace):
    workspace.data_file("app").write_text("replays: null\n")
    message = check_dataset(workspace, "app")
    assert message.startswith("datasets: 'app' is outdated")
    assert "guimauve data sync" in message


def test_missing_module_fails(workspace, pkg_root):
    _module(pkg_root).unlink()
    assert "has no generated module" in check_dataset(workspace, "app")


def test_module_without_source_hash_fails(workspace, pkg_root):
    _module(pkg_root).write_text("ALIAS = 'app'\n")
    assert "generated before SOURCE_HASH existed" in check_dataset(workspace, "app")


def test_wrong_format_version_fails(workspace, pkg_root):
    module = _module(pkg_root)
    module.write_text(module.read_text().replace("FORMAT_VERSION = 1", "FORMAT_VERSION = 0"))
    assert "older module format" in check_dataset(workspace, "app")


def test_unreadable_module_fails(workspace, pkg_root):
    _module(pkg_root).write_text("this is not python (")
    assert "unreadable generated module" in check_dataset(workspace, "app")


def test_unreadable_data_file_fails(workspace):
    workspace.data_file("app").write_text("elements: [unclosed\n")
    assert "unreadable data.yml" in check_dataset(workspace, "app")


def test_unknown_dataset_fails(workspace):
    assert "not found" in check_dataset(workspace, "nope")
