import pytest
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QPushButton

from guimauve.gui.element_editor_next import Context, start_element_editor
from guimauve.gui.element_editor_next import app as app_module
from guimauve.gui.element_editor_next.window import EditorWindow
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    """Settings of the editor in a file of the test, never the user's."""
    path = str(tmp_path / "editor.ini")
    monkeypatch.setattr(app_module, "QSettings", lambda *_: QSettings(path, QSettings.Format.IniFormat))


def click_when_shown(text: str) -> None:
    """Clicks a button of the editor window once it is open."""

    def click() -> None:
        window = next(w for w in QApplication.topLevelWidgets() if isinstance(w, EditorWindow) and w.isVisible())
        next(b for b in window.findChildren(QPushButton) if b.text() == text).click()

    QTimer.singleShot(0, click)


def context() -> Context:
    return Context(Element(name="button", x=1, y=1), Parameters().default, lambda screen: None, from_run=True)


def test_save(qapp):
    click_when_shown("Save and resume")

    result = start_element_editor(context())

    assert result.element is not None and result.element.name == "button"


def test_skip(qapp):
    click_when_shown("Skip")

    assert start_element_editor(context()).element is None


def test_theme_is_kept_between_openings(qapp):
    click_when_shown("Skip")
    start_element_editor(context())
    first = app_module._theme

    click_when_shown("Skip")
    start_element_editor(context())

    assert app_module._theme is first
    assert not qapp.windowIcon().isNull()
