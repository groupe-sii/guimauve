import pytest
from PySide6.QtWidgets import QLineEdit, QScrollArea, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import FormRow, LabelColumn
from guimauve.gui.element_editor_next.theme import METRICS


@pytest.fixture
def make_rows(qtbot):
    """Rows in a scroll area of the given width, aligned by one LabelColumn."""
    areas: list[QScrollArea] = []  # kept alive with their rows until the end of the test

    def make(width: int, editor_min: int = 40) -> list[FormRow]:
        area = QScrollArea()
        qtbot.addWidget(area)
        areas.append(area)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 0, 8, 0)
        column = LabelColumn(area.viewport(), area)
        rows = []
        for label in ("Name", "Default target"):
            editor = QLineEdit()
            editor.setMinimumWidth(editor_min)
            row = FormRow(label, editor)
            column.add(row)
            layout.addWidget(row)
            rows.append(row)
        area.setWidget(content)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.resize(width, 200)
        area.show()
        column.apply()
        return rows

    yield make


def label_widths(rows) -> list[int]:
    return [row.layout().itemAt(0).widget().width() for row in rows]


def test_column_is_a_share_of_the_width(make_rows):
    widths = label_widths(make_rows(600))

    assert widths[0] == widths[1] == round((600 - 16) * METRICS.label_ratio)


def test_column_never_below_its_minimum(make_rows):
    assert label_widths(make_rows(200)) == [METRICS.label_width] * 2


def test_column_leaves_room_for_the_editors(make_rows):
    widths = label_widths(make_rows(600, editor_min=420))

    assert widths[0] == widths[1] == 600 - 16 - 420 - METRICS.space(2)
