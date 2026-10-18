import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from guimauve.gui.element_editor_next.components import Badge, CountBadge, Section


@pytest.fixture
def section(qtbot, theme):
    section = Section("Mouse", theme)
    qtbot.addWidget(section)
    section.set_content(QLabel("Speed"))
    return section


def header(section) -> QPushButton:
    return section.findChild(QPushButton, "header")


def test_collapsed_when_shown(section):
    assert not section.is_open()


def test_click_toggles(qtbot, section):
    qtbot.mouseClick(header(section), Qt.MouseButton.LeftButton)
    assert section.is_open()
    qtbot.mouseClick(header(section), Qt.MouseButton.LeftButton)
    assert not section.is_open()


def test_keyboard_toggles(qtbot, section):
    qtbot.keyClick(header(section), Qt.Key.Key_Space)
    assert section.is_open()


def test_can_be_opened_on_request(section):
    section.set_open(True)  # e.g. a click on an issue of this section
    assert section.is_open()


def test_badges_hidden_at_zero(section):
    badges = section.findChildren(Badge) + section.findChildren(CountBadge)
    assert all(badge.isHidden() for badge in badges)


def test_badges_show_their_counts(section):
    section.set_counts(own=2, code=1, errors=1, warnings=0)
    (own,) = section.findChildren(Badge)
    code, errors, warnings = section.findChildren(CountBadge)
    assert own.text() == "2"
    assert (code.count(), errors.count()) == (1, 1)
    assert not errors.isHidden()
    assert warnings.isHidden()


def test_header_takes_the_focus_only_from_the_keyboard(section):
    assert header(section).focusPolicy() is Qt.FocusPolicy.TabFocus
