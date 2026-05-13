import time

import numpy as np
from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from guimauve.gui.common.resources import ndarray_to_qpixmap


class OverlayManager(QWidget):
    """
    Fullscreen overlay for screen capture management.
    """

    # Class-level attributes to be set in the launcher
    capture_provider = None
    initial_capture = None

    image_captured = Signal(QPixmap)
    rect_selected = Signal(QRect)

    def __init__(self):
        super().__init__()

        if OverlayManager.capture_provider is None:
            raise RuntimeError("OverlayManager.capture_provider must be set before use.")

        self._windows_to_hide = None

        # Self-destruct on close to free memory
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Window parameters for a seamless overlay
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.X11BypassWindowManagerHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        self.full_screenshot = None
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.last_mouse_pos = QPoint()
        self.is_drawing = False

        # Panning attributes
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        self.last_pan_pos = QPoint()

        self.mode = None
        self.areas = None

    def capture_image(self, windows_to_hide=None, delay=0):
        self.mode = "CAPTURE"
        self._prepare(windows_to_hide, delay, cursor=Qt.CrossCursor)

    def select_area(self, windows_to_hide=None, delay=0):
        self.mode = "SELECT"
        self._prepare(windows_to_hide, delay, cursor=Qt.CrossCursor)

    def visualize(self, areas, windows_to_hide=None, delay=0):
        self.mode = "VIEW"
        self.areas = areas if isinstance(areas, list) else [areas]
        self._prepare(windows_to_hide, delay=delay, cursor=Qt.ArrowCursor)

    def update_areas(self, areas):
        self.areas = areas if isinstance(areas, list) else [areas]
        self.update()

    def _prepare(self, windows, delay, cursor):
        self._windows_to_hide = windows or []
        self.setCursor(cursor)

        for win in self._windows_to_hide:
            win.hide()

        self._capture(delay)

    def _capture(self, delay):
        """Grabs the screen from provider."""
        if delay == -1:
            self._show(OverlayManager.initial_capture)
            return

        # Small 300ms buffer even for 'instant' to let the OS hide the window
        time.sleep(max(0.3, int(delay)))

        capture = OverlayManager.capture_provider()
        self._show(capture)

    def _show(self, capture):
        """Shows the overlay."""
        if isinstance(capture, np.ndarray):
            self.full_screenshot = ndarray_to_qpixmap(capture)
        else:
            self.full_screenshot = capture

        if self.full_screenshot:
            # Handle initial centering
            self._clamp_pan_offset()
            self.showFullScreen()
            self.activateWindow()

    def _clamp_pan_offset(self):
        """
        Constraints the pan_offset so the image stays within screen boundaries.
        If image is smaller than screen, it is centered.
        """
        if not self.full_screenshot:
            return

        ratio = self.screen().devicePixelRatio()
        screen_geo = self.screen().geometry()

        img_w = self.full_screenshot.width() / ratio
        img_h = self.full_screenshot.height() / ratio

        # X Axis Constraint
        if img_w <= screen_geo.width():
            # Smaller than screen: Force center
            new_x = (screen_geo.width() - img_w) // 2
        else:
            # Larger than screen: Clamp between [screen - image, 0]
            new_x = max(min(self.pan_offset.x(), 0), screen_geo.width() - img_w)

        # Y Axis Constraint
        if img_h <= screen_geo.height():
            # Smaller than screen: Force center
            new_y = (screen_geo.height() - img_h) // 2
        else:
            # Larger than screen: Clamp between [screen - image, 0]
            new_y = max(min(self.pan_offset.y(), 0), screen_geo.height() - img_h)

        self.pan_offset = QPoint(int(new_x), int(new_y))

    def _draw_help_text(self, painter):
        painter.save()
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        text = "L-CLICK + DRAG: Select  |  CTRL + DRAG: Move Selection  |  M-CLICK + DRAG: Move around |  ESC: Cancel"
        painter.drawText(self.rect().adjusted(0, 0, 0, -20), Qt.AlignHCenter | Qt.AlignBottom, text)
        painter.restore()

    def paintEvent(self, event):
        if not self.full_screenshot:
            return

        ratio = self.screen().devicePixelRatio()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background color (Black for empty spaces)
        painter.fillRect(self.rect(), Qt.black)

        # Background (Screenshot) drawn with constrained pan_offset
        img_rect = QRect(
            self.pan_offset.x(),
            self.pan_offset.y(),
            int(self.full_screenshot.width() / ratio),
            int(self.full_screenshot.height() / ratio),
        )
        painter.drawPixmap(img_rect, self.full_screenshot)

        # Prepare dark overlay
        path = QPainterPath()
        path.addRect(self.rect())

        rects_to_draw = []

        if self.mode == "VIEW" and self.areas:
            for a in self.areas:
                phys_x = float(a.left)
                phys_y = float(a.top)
                phys_w = float(a.right - a.left)
                phys_h = float(a.bottom - a.top)

                log_x = (phys_x / ratio) + self.pan_offset.x()
                log_y = (phys_y / ratio) + self.pan_offset.y()
                log_w = phys_w / ratio
                log_h = phys_h / ratio

                logical_rect = QRectF(log_x, log_y, log_w, log_h)
                rects_to_draw.append(logical_rect)
        else:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            if not self.start_pos.isNull() and selection_rect.width() > 2:
                rects_to_draw = [selection_rect]

        for r in rects_to_draw:
            path.addRect(r)

        path.setFillRule(Qt.OddEvenFill)
        painter.fillPath(path, QColor(0, 0, 0, 160))

        # Draw borders
        if rects_to_draw:
            if self.mode == "VIEW":
                pen = QPen(QColor(255, 0, 0), 2, Qt.SolidLine)
                painter.setPen(pen)
                for r in rects_to_draw:
                    painter.drawRect(r.adjusted(0, 0, -1, -1))
            else:
                painter.setCompositionMode(QPainter.CompositionMode_Exclusion)
                painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                for r in rects_to_draw:
                    painter.drawRect(r.adjusted(0, 0, -1, -1))
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if self.mode != "VIEW" and not self.is_drawing and not self.is_panning:
            self._draw_help_text(painter)

    def mousePressEvent(self, event):
        pos = event.position().toPoint()

        # Panning with Middle Button (Wheel click)
        if event.button() == Qt.MiddleButton and not self.is_drawing:
            self.is_panning = True
            self.last_pan_pos = pos
            self.setCursor(Qt.ClosedHandCursor)
            return

        if self.mode == "VIEW":
            return

        if event.button() == Qt.LeftButton:
            self.start_pos = pos
            self.end_pos = pos
            self.last_mouse_pos = pos
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        current_pos = event.position().toPoint()

        # Handle Panning logic
        if self.is_panning:
            delta = current_pos - self.last_pan_pos
            self.pan_offset += delta
            self._clamp_pan_offset()  # Apply constraints immediately
            self.last_pan_pos = current_pos
            self.update()
            return

        # Handle Selection logic
        if self.is_drawing:
            if event.modifiers() & Qt.ControlModifier:
                delta = current_pos - self.last_mouse_pos
                self.start_pos += delta
                self.end_pos += delta
            else:
                self.end_pos = current_pos
            self.last_mouse_pos = current_pos
            self.update()

    def mouseReleaseEvent(self, event):
        # Stop Panning
        if event.button() == Qt.MiddleButton and self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CrossCursor)
            return

        if self.mode == "VIEW":
            return

        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            final_rect = QRect(self.start_pos, self.end_pos).normalized()

            if final_rect.isValid() and final_rect.width() > 5:
                ratio = self.screen().devicePixelRatio()

                # Convert screen logical coordinates to image physical coordinates
                relative_rect = final_rect.translated(-self.pan_offset)

                physical_rect = QRect(
                    int(relative_rect.x() * ratio),
                    int(relative_rect.y() * ratio),
                    int(relative_rect.width() * ratio),
                    int(relative_rect.height() * ratio),
                )

                self.rect_selected.emit(physical_rect)

                if self.mode == "CAPTURE":
                    cropped_pixmap = self.full_screenshot.copy(physical_rect)
                    self.image_captured.emit(cropped_pixmap)

            self.close()

    def closeEvent(self, event):
        """Restore parent window visibility before the capturer is destroyed."""
        for window in self._windows_to_hide:
            window.show()
            window.raise_()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
