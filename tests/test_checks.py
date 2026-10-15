import logging
import platform

import pytest

from guimauve.checks import CheckFailure, EnvironmentCheckError, check_datasets, check_scaling, check_screen_size
from guimauve.storage.sync import sync_dataset
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.screen import get_primary_scaling


def test_error_keeps_failures():
    failures = [CheckFailure("scaling", "expected 100%, got 125%")]
    error = EnvironmentCheckError(failures)
    assert error.failures == failures


def test_error_is_a_runtime_error():
    with pytest.raises(RuntimeError):
        raise EnvironmentCheckError([CheckFailure("scaling", "x")])


def test_message_singular():
    message = str(EnvironmentCheckError([CheckFailure("scaling", "expected 100%, got 125%")]))
    assert "(1 failure)" in message
    assert "  - scaling: expected 100%, got 125%" in message


def test_message_lists_every_failure():
    message = str(
        EnvironmentCheckError(
            [
                CheckFailure("screen_size", "expected 1920x1080, got 1280x720"),
                CheckFailure("datasets", "'login' is outdated"),
            ]
        )
    )
    assert "(2 failures)" in message
    assert "screen_size: expected 1920x1080, got 1280x720" in message
    assert "datasets: 'login' is outdated" in message


# ============ check_datasets ============


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


def _messages(failures):
    return [f.message for f in failures]


def test_disabled_checks_nothing(workspace):
    workspace.data_file("app").write_text("replays: null\n")  # outdated, but the check is off
    assert check_datasets(workspace, False) == []


@pytest.mark.parametrize("selection", [True, ["app"]])
def test_up_to_date_dataset_passes(workspace, selection):
    assert check_datasets(workspace, selection) == []


def test_comment_only_change_passes(workspace):
    workspace.data_file("app").write_text("# just a comment\n")
    assert check_datasets(workspace, True) == []


def test_changed_data_file_fails(workspace):
    workspace.data_file("app").write_text("replays: null\n")
    failures = check_datasets(workspace, True)
    assert [f.check for f in failures] == ["datasets"]
    assert "'app'" in failures[0].message
    assert "changed since the last sync" in failures[0].message
    assert "guimauve data sync" in failures[0].message


def test_missing_module_fails(workspace, pkg_root):
    _module(pkg_root).unlink()
    assert "module not generated" in _messages(check_datasets(workspace, True))[0]


def test_module_without_source_hash_fails(workspace, pkg_root):
    _module(pkg_root).write_text("ALIAS = 'app'\n")
    assert "no SOURCE_HASH" in _messages(check_datasets(workspace, True))[0]


def test_wrong_format_version_fails(workspace, pkg_root):
    module = _module(pkg_root)
    module.write_text(module.read_text().replace("FORMAT_VERSION = 1", "FORMAT_VERSION = 0"))
    assert "format is 0, expected 1" in _messages(check_datasets(workspace, True))[0]


def test_unreadable_module_fails(workspace, pkg_root):
    _module(pkg_root).write_text("this is not python (")
    assert "cannot read the generated module" in _messages(check_datasets(workspace, True))[0]


def test_unreadable_data_file_fails(workspace):
    workspace.data_file("app").write_text("elements: [unclosed\n")
    assert "cannot read data.yml" in _messages(check_datasets(workspace, True))[0]


def test_unknown_named_dataset_fails(workspace):
    assert "dataset not found" in _messages(check_datasets(workspace, ["nope"]))[0]


def test_true_checks_every_dataset(workspace):
    workspace.create_dataset("other")
    sync_dataset(workspace, "other")
    workspace.data_file("other").write_text("replays: null\n")

    failures = check_datasets(workspace, True)
    assert len(failures) == 1
    assert "'other'" in failures[0].message


def test_list_checks_only_named_datasets(workspace):
    workspace.create_dataset("other")  # never synced, but not selected
    assert check_datasets(workspace, ["app"]) == []


def test_every_failure_is_reported(workspace, pkg_root):
    workspace.create_dataset("other")  # never synced
    workspace.data_file("app").write_text("replays: null\n")
    assert len(check_datasets(workspace, True)) == 2


def test_no_dataset_is_skipped_with_warning(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert check_datasets(DataWorkspace(tmp_path / "empty"), True) == []
    assert "Dataset check skipped" in caplog.text


# ============ check_screen_size ============


def test_screen_size_disabled_does_not_capture(fake_driver):
    assert check_screen_size(None, fake_driver) == []
    assert fake_driver.calls == []


def test_screen_size_matching_passes(fake_driver):
    assert check_screen_size((1920, 1080), fake_driver) == []  # FakeDriver is 1920x1080


def test_screen_size_mismatch_fails(fake_driver):
    failures = check_screen_size((1280, 720), fake_driver)
    assert [f.check for f in failures] == ["screen_size"]
    assert failures[0].message == "expected 1280x720, got 1920x1080"


# ============ check_scaling ============


@pytest.fixture
def windows(monkeypatch):
    """Pretends to run on Windows, with a primary monitor scaled at 125%."""
    monkeypatch.setattr("guimauve.checks.platform.system", lambda: "Windows")
    monkeypatch.setattr("guimauve.checks.get_primary_scaling", lambda: 125)


def test_scaling_disabled_checks_nothing():
    assert check_scaling(None, "local") == []


def test_scaling_matching_passes(windows):
    assert check_scaling(125, "local") == []


def test_scaling_mismatch_fails(windows):
    failures = check_scaling(100, "local")
    assert [f.check for f in failures] == ["scaling"]
    assert failures[0].message == "expected 100%, got 125%"


def test_scaling_skipped_in_vnc_mode(windows, caplog):
    with caplog.at_level(logging.WARNING):
        assert check_scaling(100, "vnc") == []
    assert "Scaling check skipped" in caplog.text


def test_scaling_skipped_outside_windows(monkeypatch, caplog):
    monkeypatch.setattr("guimauve.checks.platform.system", lambda: "Linux")
    with caplog.at_level(logging.WARNING):
        assert check_scaling(100, "local") == []
    assert "Scaling check skipped" in caplog.text


def test_scaling_skipped_when_unreadable(windows, monkeypatch, caplog):
    def fail():
        raise OSError("boom")

    monkeypatch.setattr("guimauve.checks.get_primary_scaling", fail)
    with caplog.at_level(logging.WARNING):
        assert check_scaling(100, "local") == []
    assert "cannot read the display scaling" in caplog.text


@pytest.mark.skipif(platform.system() != "Windows", reason="reads the real Windows display scaling")
def test_get_primary_scaling_on_real_windows():
    assert get_primary_scaling() >= 100
