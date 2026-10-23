import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.canvas import CanvasView
from guimauve.gui.element_editor_next.canvas import zoom as zooms
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.theme import METRICS

VIEW_WIDTH, VIEW_HEIGHT = 600, 400
NONE = Qt.MouseButton.NoButton
MIDDLE = Qt.MouseButton.MiddleButton


def picture(width: int, height: int):
    image = np.zeros((height, width, 3), np.uint8)
    image[..., 0] = 200
    image[0, 0] = (1, 2, 3)
    return to_qimage(image)


@pytest.fixture
def view(theme, qtbot):
    widget = CanvasView(theme)
    qtbot.addWidget(widget)
    widget.resize(VIEW_WIDTH, VIEW_HEIGHT)
    widget.show()
    return widget


def mouse(view, kind: QEvent.Type, point: QPointF, button=NONE, buttons=NONE) -> None:
    globally = view.viewport().mapToGlobal(point)
    event = QMouseEvent(kind, point, globally, button, buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view.viewport(), event)


def drag(view, start: QPointF, end: QPointF, button=MIDDLE) -> None:
    mouse(view, QEvent.Type.MouseButtonPress, start, button, button)
    mouse(view, QEvent.Type.MouseMove, end, NONE, button)
    mouse(view, QEvent.Type.MouseButtonRelease, end, button, NONE)


def wheel(view, point: QPointF, notches: int) -> None:
    event = QWheelEvent(
        point,
        view.viewport().mapToGlobal(point),
        QPoint(),
        QPoint(0, 120 * notches),
        NONE,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view.viewport(), event)


def centre(view) -> QPointF:
    return view.to_image(QRectF(view.viewport().rect()).center())


def available(length: int) -> float:
    return length - 2 * METRICS.canvas_margin


def test_image_fits_the_view(view):
    view.set_image(picture(1000, 500))

    assert view.zoom == pytest.approx(min(available(VIEW_WIDTH) / 1000, available(VIEW_HEIGHT) / 500))
    assert view.is_fitting()
    assert centre(view).x() == pytest.approx(500, abs=1)
    assert centre(view).y() == pytest.approx(250, abs=1)


def test_small_image_fits_enlarged_twice_at_most(view):
    view.set_image(picture(100, 50))

    assert view.zoom == zooms.FIT_MAX


def test_keeps_fitting_when_resized(view):
    view.set_image(picture(1000, 500))

    view.resize(VIEW_WIDTH // 2, VIEW_HEIGHT)

    assert view.zoom == pytest.approx(available(VIEW_WIDTH // 2) / 1000)


def test_zoom_stops_fitting(view):
    view.set_image(picture(1000, 500))
    view.set_zoom(1.0)

    view.resize(VIEW_WIDTH // 2, VIEW_HEIGHT)

    assert view.zoom == 1.0
    assert not view.is_fitting()


def test_zoom_changed_is_emitted(view, qtbot):
    view.set_image(picture(1000, 500))

    with qtbot.waitSignal(view.zoom_changed):
        view.zoom_in()

    assert view.zoom == zooms.zoom_in(0.552)


def test_zoom_without_image_does_nothing(view):
    view.set_zoom(4.0)

    assert view.zoom == 1.0


def test_wheel_zooms_on_the_cursor(view):
    view.set_image(picture(1000, 500))
    point = QPointF(150, 120)
    before = view.to_image(point)

    wheel(view, point, 2)

    assert view.zoom == pytest.approx(zooms.wheel(0.552, 2))
    after = view.to_image(point)
    assert after.x() == pytest.approx(before.x(), abs=2)
    assert after.y() == pytest.approx(before.y(), abs=2)


def test_middle_drag_moves_the_view(view):
    view.set_image(picture(1000, 500))
    view.set_zoom(2.0)
    before = centre(view)

    drag(view, QPointF(300, 200), QPointF(200, 150))

    after = centre(view)
    assert after.x() == pytest.approx(before.x() + 50, abs=1)
    assert after.y() == pytest.approx(before.y() + 25, abs=1)


def test_left_drag_moves_the_view(view):
    view.set_image(picture(1000, 500))
    view.set_zoom(2.0)
    before = centre(view)

    drag(view, QPointF(300, 200), QPointF(320, 200), Qt.MouseButton.LeftButton)

    assert centre(view).x() == pytest.approx(before.x() - 10, abs=1)


def test_the_view_stays_on_the_image(view):
    view.set_image(picture(1000, 500))
    view.set_zoom(1.0)

    drag(view, QPointF(300, 200), QPointF(-5000, -5000))

    assert centre(view).x() == pytest.approx(1000, abs=1)
    assert centre(view).y() == pytest.approx(500, abs=1)


def test_pixel_under_the_mouse(view, qtbot):
    view.set_image(picture(100, 50))
    corner = view.viewportTransform().map(QPointF(0.5, 0.5))

    with qtbot.waitSignal(view.hovered_changed):
        mouse(view, QEvent.Type.MouseMove, corner)

    assert view.hovered_pixel() == QPoint(0, 0)
    assert view.hovered_color().name() == "#010203"


def test_no_pixel_outside_the_image_or_the_view(view):
    view.set_image(picture(100, 50))
    mouse(view, QEvent.Type.MouseMove, view.viewportTransform().map(QPointF(10.5, 10.5)))

    mouse(view, QEvent.Type.MouseMove, QPointF(2, 2))
    assert view.hovered_pixel() is None

    mouse(view, QEvent.Type.MouseMove, view.viewportTransform().map(QPointF(10.5, 10.5)))
    QApplication.sendEvent(view.viewport(), QEvent(QEvent.Type.Leave))
    assert view.hovered_pixel() is None
    assert view.hovered_color() is None


@pytest.mark.parametrize(
    ("level", "mode"),
    [(0.5, Qt.TransformationMode.SmoothTransformation), (2.0, Qt.TransformationMode.FastTransformation)],
)
def test_pixels_stay_sharp_beyond_actual_size(view, level, mode):
    view.set_image(picture(1000, 500))

    view.set_zoom(level)

    assert view.scene().items()[0].transformationMode() == mode


def test_no_image(view):
    view.set_image(picture(100, 50))

    view.set_image(None)

    assert view.image() is None
    assert view.hovered_pixel() is None
