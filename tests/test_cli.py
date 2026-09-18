from guimauve import cli
from guimauve.cli import main


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


def test_bare_data_group_returns_1():
    assert main(["data"]) == 1
