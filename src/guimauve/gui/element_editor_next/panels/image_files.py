"""Asking for an image file to import, and telling when it cannot be read."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from guimauve.gui.element_editor_next.services import IMAGE_FILTER

UNREADABLE = "This file is not an image Guimauve can read."


def ask_image_file(parent: QWidget) -> Path | None:
    """Asks for an image file to import; None when cancelled."""
    path, _ = QFileDialog.getOpenFileName(parent, "Import an image", "", IMAGE_FILTER)
    return Path(path) if path else None


def warn(parent: QWidget, text: str) -> None:
    QMessageBox.warning(parent, "Import an image", text)
