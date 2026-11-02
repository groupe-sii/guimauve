import warnings

import pytest

from guimauve.gui import legacy_editor_enabled


@pytest.mark.parametrize("value", [None, "", "  "], ids=["absent", "empty", "blank"])
def test_new_editor_by_default(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("GUIMAUVE_EDITOR", raising=False)
    else:
        monkeypatch.setenv("GUIMAUVE_EDITOR", value)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert not legacy_editor_enabled()


@pytest.mark.parametrize("value", ["legacy", "Legacy", " LEGACY "])
def test_legacy_editor_whatever_the_case(monkeypatch, value):
    monkeypatch.setenv("GUIMAUVE_EDITOR", value)

    assert legacy_editor_enabled()


@pytest.mark.parametrize("value", ["next", "old"])
def test_unknown_value_warns_and_keeps_the_new_editor(monkeypatch, value):
    monkeypatch.setenv("GUIMAUVE_EDITOR", value)

    with pytest.warns(UserWarning, match=f"GUIMAUVE_EDITOR='{value}'.*legacy"):
        assert not legacy_editor_enabled()
