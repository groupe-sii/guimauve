from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from guimauve import cli
from guimauve.cli import main
from guimauve.gui.element_editor import EditorResult
from guimauve.models.element import Element


def _spy(store):
    def fn(args):
        store["args"] = args
        return 0

    return fn


# --- dispatch: routing + argument parsing ---


def test_add_dispatch_parses_names(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_add", _spy(store))

    assert main(["data", "add", "app1", "app2"]) == 0
    assert store["args"].names == ["app1", "app2"]


def test_sync_dispatch(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_sync", _spy(store))

    assert main(["data", "sync"]) == 0
    assert "args" in store


def test_edit_dispatch_parses_name_element_and_vnc(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_edit", _spy(store))

    assert main(["data", "edit", "app", "LOGIN", "--vnc", "params.yml"]) == 0
    assert store["args"].name == "app"
    assert store["args"].element == "LOGIN"
    assert store["args"].vnc == "params.yml"


def test_edit_dispatch_vnc_defaults_to_none(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_edit", _spy(store))

    main(["data", "edit", "app", "LOGIN"])
    assert store["args"].vnc is None


def test_list_dispatch(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_list", _spy(store))

    assert main(["data", "list"]) == 0
    assert "args" in store


def test_remove_dispatch_parses_names(monkeypatch):
    store = {}
    monkeypatch.setattr(cli, "cmd_remove", _spy(store))

    assert main(["data", "remove", "app1", "app2"]) == 0
    assert store["args"].names == ["app1", "app2"]


# --- no command / bare group ---


def test_no_command_returns_1():
    assert main([]) == 1


# --- logging options ---


@pytest.fixture
def logging_setup(monkeypatch):
    """Records the calls to setup_logging instead of configuring the logs."""
    calls = []
    monkeypatch.setattr(cli, "setup_logging", lambda level, levels: calls.append((level, levels)))
    monkeypatch.setattr(cli, "cmd_sync", lambda args: 0)
    return calls


def test_no_logs_without_option(logging_setup):
    main(["data", "sync"])
    assert logging_setup == []


@pytest.mark.parametrize(
    ("argv", "level"),
    [
        (["-v", "data", "sync"], "INFO"),
        (["data", "sync", "-v"], "INFO"),
        (["data", "sync", "-vv"], "DEBUG"),
        (["-vvv", "data", "sync"], "DEBUG"),
    ],
)
def test_verbose_before_or_after_the_command(logging_setup, argv, level):
    main(argv)
    assert logging_setup == [(level, {})]


def test_log_sets_the_level_of_a_part(logging_setup):
    main(["data", "sync", "--log", "drivers=DEBUG", "--log", "detection=INFO"])
    assert logging_setup == [("WARNING", {"drivers": "DEBUG", "detection": "INFO"})]


def test_log_without_level_is_refused(logging_setup):
    with pytest.raises(SystemExit):
        main(["data", "sync", "--log", "drivers"])


def test_bare_data_group_returns_1():
    assert main(["data"]) == 1


# --- edit: choice of the element editor ---


@pytest.fixture
def edit_run(monkeypatch, fake_driver):
    """cmd_edit on an existing element, without workspace or screen; returns what was saved."""
    saved = []
    module = SimpleNamespace(Elements=SimpleNamespace(BUTTON=Element(name="BUTTON", x=1, y=1)))

    @contextmanager
    def driver(vnc_file):
        yield fake_driver

    monkeypatch.setattr(cli, "DataWorkspace", lambda: SimpleNamespace(exists=lambda name: True))
    monkeypatch.setattr(cli, "importlib", SimpleNamespace(import_module=lambda name: module))
    monkeypatch.setattr(cli, "_driver", driver)
    monkeypatch.setattr(cli, "save_element", lambda workspace, name, element: saved.append(element))
    monkeypatch.setattr(cli, "sync_dataset", lambda workspace, name: None)

    def run() -> list:
        assert main(["data", "edit", "app", "BUTTON"]) == 0
        return saved

    return run


def test_edit_opens_the_new_editor_by_default(monkeypatch, edit_run):
    import guimauve.gui.element_editor as editor

    monkeypatch.delenv("GUIMAUVE_EDITOR", raising=False)
    contexts = []
    edited = Element(name="BUTTON", x=5, y=1)
    monkeypatch.setattr(
        editor, "start_element_editor", lambda context: contexts.append(context) or EditorResult(edited)
    )

    assert edit_run() == [edited]
    (context,) = contexts
    assert context.element.name == "BUTTON" and not context.from_run


def test_edit_opens_the_legacy_editor_with_the_variable(monkeypatch, edit_run):
    import guimauve.gui.element_editor_legacy as legacy_editor

    monkeypatch.setenv("GUIMAUVE_EDITOR", "legacy")
    contexts = []
    monkeypatch.setattr(
        legacy_editor, "start_element_editor", lambda context: contexts.append(context) or (context.element, False)
    )

    assert edit_run() == []
    assert contexts and not hasattr(contexts[0], "code_overrides")


def test_edit_help_tells_how_to_open_the_legacy_editor(capsys):
    with pytest.raises(SystemExit):
        main(["data", "edit", "-h"])

    assert "GUIMAUVE_EDITOR=legacy" in capsys.readouterr().out
