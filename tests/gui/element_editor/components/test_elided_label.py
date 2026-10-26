import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import ElidedLabel

LONG = "Sign in with your company account to continue " * 4


@pytest.fixture
def label(qtbot):
    label = ElidedLabel()
    qtbot.addWidget(label)
    label.show()  # a hidden widget gets its resize events only once shown
    return label


def advance(label: ElidedLabel, text: str) -> int:
    return label.fontMetrics().horizontalAdvance(text)


def test_a_text_that_fits_is_shown_whole(label):
    label.setText("Sign in")
    label.resize(advance(label, "Sign in") + 10, 20)

    assert label.text() == label.full_text() == "Sign in"
    assert label.toolTip() == ""


def test_a_text_too_long_ends_with_an_ellipsis_and_shows_whole_in_its_tooltip(label):
    label.setText(LONG)
    label.resize(advance(label, LONG) // 3, 20)

    expected = label.fontMetrics().elidedText(LONG, Qt.TextElideMode.ElideRight, label.contentsRect().width())
    assert label.text() == expected and expected.endswith("…")
    assert label.full_text() == LONG
    assert label.toolTip() == LONG


def test_widening_shows_the_whole_text_again(label):
    label.setText(LONG)
    label.resize(advance(label, LONG) // 3, 20)

    label.resize(advance(label, LONG) + 10, 20)

    assert label.text() == LONG
    assert label.toolTip() == ""


def test_asks_for_no_width_but_hints_the_whole_text(label):
    label.setText(LONG)

    assert label.minimumSizeHint().width() == 0
    assert label.sizeHint().width() == advance(label, LONG)


def test_a_long_text_does_not_widen_its_parent(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    label = ElidedLabel("Sign in")
    QHBoxLayout(parent).addWidget(label)
    narrow = parent.minimumSizeHint().width()

    label.setText(LONG)

    assert parent.minimumSizeHint().width() == narrow


def test_a_new_font_cuts_the_text_again(label):
    label.setText(LONG)
    label.resize(advance(label, LONG) // 2, 20)
    before = label.text()

    font = QFont(label.font())
    font.setPointSizeF(font.pointSizeF() * 2)
    label.setFont(font)

    assert label.text() != before
    assert label.text() == label.fontMetrics().elidedText(
        LONG, Qt.TextElideMode.ElideRight, label.contentsRect().width()
    )
