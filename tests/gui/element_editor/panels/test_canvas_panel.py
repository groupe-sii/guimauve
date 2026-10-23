import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QFont, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import QApplication, QLabel

from guimauve.gui.element_editor_next.canvas.top_bar import ACTUAL_SIZE, FIT, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT
from guimauve.gui.element_editor_next.panels import CanvasPanel
from guimauve.gui.element_editor_next.panels.canvas_panel import EMPTY_TITLE
from guimauve.gui.element_editor_next.state import ELEMENT
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant


@pytest.fixture
def show(theme, qtbot):
    def make(store) -> CanvasPanel:
        panel = CanvasPanel(store, theme)
        qtbot.addWidget(panel)
        panel.resize(660, 410)
        panel.show()
        return panel

    return make


def key(store, index: int) -> int:
    return store.variant_keys()[index]


def action(panel, text: str):
    return next(a for a in panel.top_bar.zoom_menu.actions() if a.text().split("\t")[0] == text)


def hover(panel, pixel: QPointF) -> None:
    point = panel.view.viewportTransform().map(pixel)
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        point,
        panel.view.viewport().mapToGlobal(point),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(panel.view.viewport(), event)


def test_shows_the_image_of_the_selected_variant(store, show):
    store.replace_image(key(store, 1), np.zeros((30, 50, 3), np.uint8))

    panel = show(store)
    assert panel.view.image().width() == 120

    store.select(key(store, 1))
    assert (panel.view.image().width(), panel.view.image().height()) == (50, 30)


def test_a_new_image_fits_again(store, show):
    panel = show(store)
    panel.view.set_zoom(4.0)

    store.crop(key(store, 0), Area(left=0, top=0, right=60, bottom=40))

    assert panel.view.is_fitting()
    assert panel.view.image().width() == 60


def test_other_edits_keep_the_zoom(store, show):
    panel = show(store)
    panel.view.set_zoom(4.0)

    store.set_field(ELEMENT, "timeout", 9)
    store.move_target(store.document.key(store.document.variants[0].targets[0]), 50, 30)

    assert panel.view.zoom == 4.0


def test_variant_without_image_shows_how_to_capture(make_store, show):
    panel = show(make_store([ImageVariant(name="empty")]))

    assert panel.empty.isVisible()
    assert panel.view.image() is None
    assert not panel.top_bar.zoom_button.isVisible()
    assert EMPTY_TITLE in [label.text() for label in panel.empty.findChildren(QLabel)]


def test_text_variant_shows_the_background_only(store, show, text_variant):
    store.add_variant(text_variant)

    panel = show(store)

    assert not panel.empty.isVisible()
    assert panel.view.image() is None
    assert not panel.status_bar.size_label.isVisible()


def test_status_bar_shows_the_image_and_the_pixel(store, show):
    store.replace_image(key(store, 0), np.full((40, 120, 3), (45, 107, 216), np.uint8))
    panel = show(store)
    status = panel.status_bar

    assert status.size_label.text() == "Image 120 × 40 px"
    assert status.position.text() == "–"
    assert not status.color.isVisible()

    hover(panel, QPointF(12.5, 7.5))

    assert status.position.text() == "x 12, y 7"
    assert status.color.text() == "#2D6BD8"
    assert status.color.isVisible()


def test_numbers_use_tabular_digits(store, show):
    panel = show(store)

    for widget in (panel.status_bar.position, panel.status_bar.size_label, panel.top_bar.zoom_button):
        assert widget.font().featureValue(QFont.Tag("tnum")) == 1


def test_zoom_menu(store, show):
    panel = show(store)

    action(panel, "200 %").trigger()
    assert panel.view.zoom == 2.0
    assert panel.top_bar.zoom_button.text() == "200 %"

    action(panel, "Actual size (100 %)").trigger()
    assert panel.view.zoom == 1.0

    action(panel, "Fit to window").trigger()
    assert panel.view.is_fitting()


def test_zoom_buttons(store, show):
    panel = show(store)
    panel.view.set_zoom(1.0)

    panel.top_bar.zoom_in.click()
    assert panel.view.zoom == 1.5

    panel.top_bar.zoom_out.click()
    panel.top_bar.zoom_out.click()
    assert panel.view.zoom == 0.75


def test_zoom_shortcuts_are_bound(store, show):
    panel = show(store)

    keys = {shortcut.key() for shortcut in panel.findChildren(QShortcut)}

    assert keys >= {QKeySequence(k) for k in (FIT, ACTUAL_SIZE, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT)}
