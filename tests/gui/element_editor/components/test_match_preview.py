import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

from guimauve.gui.element_editor_next.components import MatchPreview
from guimauve.gui.element_editor_next.components.match_preview import _place
from guimauve.gui.element_editor_next.theme import METRICS


@pytest.fixture
def preview(theme, qtbot):
    widget = MatchPreview(theme)
    qtbot.addWidget(widget)
    return widget


def image(width: int, height: int) -> QImage:
    picture = QImage(width, height, QImage.Format.Format_RGB888)
    picture.fill(0)
    return picture


def test_a_small_match_shows_at_its_real_size(preview):
    preview.show_match(image(80, 40), [(10, 10), (30, 10), (30, 20), (10, 20)], (20, 15), True, QRect(0, 500, 400, 30))

    assert preview.scale == 1 and preview.isVisible()
    assert (preview.width(), preview.height()) == (80, 40)  # the image fills the preview


def test_a_large_match_is_reduced_to_the_preview(preview):
    preview.show_match(image(2 * METRICS.preview_width, 100), [], (5, 5), False, QRect(0, 500, 400, 30))

    assert preview.scale == 0.5


def test_placed_above_the_row_or_under_it_without_room():
    room, top_row, right_row = QRect(0, 0, 1000, 800), QRect(20, 10, 300, 30), QRect(950, 400, 300, 30)

    assert _place(100, 50, QRect(20, 400, 300, 30), room).y() == 400 - METRICS.space(1) - 50
    assert _place(100, 50, top_row, room).y() == top_row.bottom() + METRICS.space(1)
    assert _place(100, 50, right_row, room).x() == room.right() - 100
