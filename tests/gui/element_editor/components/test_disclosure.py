import pytest
from PySide6.QtWidgets import QLabel, QPushButton

from guimauve.gui.element_editor_next.components import Disclosure


@pytest.fixture
def group(theme, qtbot):
    group = Disclosure("Advanced", theme)
    group.add(QLabel("setting"))
    group.set_count(9)
    qtbot.addWidget(group)
    group.show()
    return group


def title(group) -> str:
    return next(label.text() for label in group.findChildren(QLabel) if label.text().startswith("Advanced"))


def test_collapsed_at_first(group):
    assert not group.is_open()


def test_title_counts_the_settings(group):
    assert title(group) == "Advanced, 9 settings"
    group.set_count(1)
    assert title(group) == "Advanced, 1 setting"


def test_header_toggles_the_settings(group):
    header = group.findChild(QPushButton, "header")

    header.click()
    assert group.is_open()
    header.click()
    assert not group.is_open()
