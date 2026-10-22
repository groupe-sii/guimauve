import pytest
from PySide6.QtGui import QFont, QFontMetrics

from guimauve.gui.element_editor_next.components import fit_text


@pytest.fixture
def metrics(qapp):
    return QFontMetrics(QFont())


def width(metrics, text: str) -> int:
    return metrics.horizontalAdvance(text)


def test_text_that_fits_is_unchanged(metrics):
    assert fit_text("Search area", metrics, width(metrics, "Search area")) == "Search area"


def test_words_wrap_on_two_lines(metrics):
    assert fit_text("Search area", metrics, width(metrics, "Search ")) == "Search\narea"


def test_one_word_ends_with_an_ellipsis(metrics):
    shown = fit_text("Direction", metrics, width(metrics, "Direc"))

    assert shown.endswith("…") and "\n" not in shown


def test_second_line_is_elided(metrics):
    shown = fit_text("Minimum number of points", metrics, width(metrics, "Minimum num"))

    first, second = shown.split("\n")
    assert first == "Minimum" and second.endswith("…")


def test_one_line_only(metrics):
    assert "\n" not in fit_text("{Y then X}", metrics, width(metrics, "{Y th"), lines=1)
