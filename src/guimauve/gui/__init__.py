import os
import warnings

EDITOR_VARIABLE = "GUIMAUVE_EDITOR"

# Silence the DPI awareness warning if it hasn't been set yet
if "QT_LOGGING_RULES" not in os.environ:
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

_OPENCV_QT_VARIABLES = ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR")


def drop_opencv_qt_paths() -> None:
    """Removes the Qt paths that the OpenCV of PaddleX (opencv-contrib-python) sets on Linux when imported.

    They point to the Qt 5 it bundles, where PySide6 finds no platform plugin it can load, so no window opens.
    cv2 is imported first, so that a later import does not set them again.
    """
    import cv2

    opencv_dir = os.path.dirname(cv2.__file__)
    for variable in _OPENCV_QT_VARIABLES:
        if os.environ.get(variable, "").startswith(opencv_dir):
            del os.environ[variable]


drop_opencv_qt_paths()


def legacy_editor_enabled() -> bool:
    """Whether GUIMAUVE_EDITOR=legacy asks for the old element editor, kept as a fallback.

    The new editor opens otherwise; a value other than legacy is reported by a warning.
    """
    value = os.environ.get(EDITOR_VARIABLE, "").strip().lower()
    if value and value != "legacy":
        warnings.warn(
            f"{EDITOR_VARIABLE}={value!r} is unknown, the new editor opens; set it to 'legacy' for the old one.",
            stacklevel=2,
        )
    return value == "legacy"
