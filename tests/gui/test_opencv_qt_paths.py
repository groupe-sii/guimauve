import os

import cv2
import pytest

from guimauve.gui import drop_opencv_qt_paths

OPENCV_QT = os.path.join(os.path.dirname(cv2.__file__), "qt", "plugins")


@pytest.mark.parametrize("variable", ["QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR"])
def test_the_qt_paths_of_opencv_are_dropped(monkeypatch, variable):
    """Set on Linux by the OpenCV of PaddleX, they would make PySide6 look for its plugins in the Qt 5 of OpenCV."""
    monkeypatch.setenv(variable, OPENCV_QT)

    drop_opencv_qt_paths()

    assert variable not in os.environ


def test_other_qt_paths_are_kept(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM_PLUGIN_PATH", "/opt/qt/plugins")

    drop_opencv_qt_paths()

    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == "/opt/qt/plugins"
