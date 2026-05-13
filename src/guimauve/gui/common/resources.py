from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer


def get_themed_icon(icon_name: str, folder_path: Path) -> QIcon:
    icon_file = folder_path / f"{icon_name}.svg"
    if not icon_file.exists():
        return QIcon()

    color_hex = QGuiApplication.palette().color(QPalette.WindowText).name()

    try:
        svg_data = icon_file.read_text(encoding="utf-8")
        themed_svg = svg_data.replace('stroke="currentColor"', f'stroke="{color_hex}"')

        pixmap = QPixmap(QSize(128, 128))
        pixmap.fill(Qt.transparent)

        renderer = QSvgRenderer(themed_svg.encode("utf-8"))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
    except Exception:
        return QIcon()


def ndarray_to_qpixmap(array: np.ndarray, copy: bool = True) -> QPixmap:
    if array is None or array.size == 0:
        return QPixmap()

    h, w, c = array.shape
    if c == 3:
        fmt = QImage.Format.Format_RGB888
    elif c == 4:
        fmt = QImage.Format.Format_RGBA8888
    else:
        fmt = QImage.Format.Format_Grayscale8

    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)

    q_img = QImage(array.data, w, h, c * w, fmt)

    return QPixmap.fromImage(q_img.copy() if copy else q_img)


def qpixmap_to_ndarray(pixmap: QPixmap, copy: bool = True) -> np.ndarray:
    if pixmap.isNull():
        return np.empty((0, 0, 3), dtype=np.uint8)

    qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    h, w = qimg.height(), qimg.width()

    bpl = qimg.bytesPerLine()
    ptr = qimg.bits()

    arr = np.frombuffer(ptr, np.uint8).reshape((h, bpl))
    arr = arr[:, : w * 3].reshape((h, w, 3))

    return arr.copy() if copy else arr
