import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLabel, QPushButton

from guimauve.gui.element_editor_next.components import Section


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "sections.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def make_section(qtbot, theme, settings):
    def make(auto_open: bool = True, has_error: bool = False) -> Section:
        section = Section("mouse", "Mouse", theme, settings)
        qtbot.addWidget(section)
        section.set_content(QLabel("Speed"))
        section.set_auto_open(auto_open, has_error)
        return section

    return make


def click(qtbot, section):
    qtbot.mouseClick(section.findChild(QPushButton, "header"), Qt.MouseButton.LeftButton)


def test_opens_as_the_panel_asks(make_section):
    assert make_section(auto_open=True).is_open()
    assert not make_section(auto_open=False).is_open()


def test_manual_collapse_is_kept(qtbot, make_section):
    click(qtbot, make_section())
    assert not make_section(auto_open=True).is_open()


def test_opening_by_hand_forgets_the_collapse(qtbot, make_section):
    section = make_section()
    click(qtbot, section)
    click(qtbot, section)
    assert section.is_open()
    assert make_section(auto_open=True).is_open()


def test_an_error_opens_a_collapsed_section(qtbot, make_section):
    click(qtbot, make_section())
    assert make_section(auto_open=False, has_error=True).is_open()


def test_keyboard_toggles(qtbot, make_section):
    section = make_section()
    qtbot.keyClick(section.findChild(QPushButton, "header"), Qt.Key.Key_Space)
    assert not section.is_open()


def test_summary_only_while_collapsed(make_section):
    section = make_section(auto_open=False)
    section.set_summary("Not set")
    summary = next(label for label in section.findChildren(QLabel) if label.text() == "Not set")
    assert not summary.isHidden()
    section.set_auto_open(True)
    assert summary.isHidden()


def test_badge_hidden_at_zero(make_section):
    section = make_section()
    badge = next(label for label in section.findChildren(QLabel) if label.property("badge"))
    assert badge.isHidden()
    section.set_badge(2)
    assert not badge.isHidden()
    assert badge.text() == "2"
