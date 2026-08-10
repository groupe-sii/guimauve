from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QToolButton

from guimauve.gui.common.resources import qpixmap_to_ndarray
from guimauve.gui.element_editor.icons import icons
from guimauve.gui.element_editor.widgets.image.test_dialog import TestDialog
from guimauve.gui.element_editor.widgets.overlay_manager import OverlayManager
from guimauve.gui.element_editor.workers.feature import FeatureWorker
from guimauve.gui.element_editor.workers.ocr import OcrWorker
from guimauve.gui.element_editor.workers.template import TemplateWorker
from guimauve.models.area import Area

WORKERS = {"template": TemplateWorker, "feature": FeatureWorker, "ocr": OcrWorker}


class TestButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setIcon(icons.TEST)
        self.setToolTip("Test")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAutoRaise(True)

        self.overlay = None
        self.test_dialog = None
        self.worker = None

        self._init_ui()
        self._init_signals()

    def _trigger_capture(self, delay=0):
        windows = self.window().get_visible_windows()
        self.overlay = OverlayManager()
        self.overlay.visualize([], windows_to_hide=windows, delay=delay)

        default = self.window().context.default
        self.test_dialog = TestDialog(default)
        self.test_dialog.test_requested.connect(self._on_test_requested)
        self.test_dialog.finished.connect(self.overlay.close)
        self.overlay.destroyed.connect(self.test_dialog.close)
        self.test_dialog.show()

    def _on_test_requested(self, mode, params):
        self.overlay.update_areas([])
        variant = self.window().element_manager.current_variant
        to_find = variant.image
        if variant.match_area:
            y_start = variant.match_area.top
            y_end = variant.match_area.bottom
            x_start = variant.match_area.left
            x_end = variant.match_area.right
            to_find = to_find[y_start:y_end, x_start:x_end]

        if to_find is None:
            return

        self.test_dialog.set_running(True)

        worker_class = WORKERS[mode]
        self.worker = worker_class(qpixmap_to_ndarray(self.overlay.full_screenshot), to_find, params)

        self.worker.finished.connect(self._on_test_worker_finished)
        self.worker.start()

    def _on_test_worker_finished(self):
        self.test_dialog.set_running(False)
        self.test_dialog.set_result(len(self.worker.results))

        areas = [
            Area(left=r.box.tl[0], top=r.box.tl[1], right=r.box.br[0], bottom=r.box.br[1]) for r in self.worker.results
        ]

        self.overlay.update_areas(areas)

    def _init_ui(self):
        menu = QMenu(self)

        self.act_instant = QAction("Instant", icon=icons.INSTANT, parent=self)
        self.act_initial = QAction("Initial", icon=icons.INITIAL, parent=self)

        delay_menu = QMenu("Delay", icon=icons.TIMER, parent=self)

        self.act_delay_3s = QAction("3 sec", self)
        self.act_delay_5s = QAction("5 sec", self)
        self.act_delay_10s = QAction("10 sec", self)

        delay_menu.addActions([self.act_delay_3s, self.act_delay_5s, self.act_delay_10s])

        menu.addAction(self.act_instant)
        menu.addAction(self.act_initial)
        menu.addMenu(delay_menu)

        self.setMenu(menu)

    def _init_signals(self):
        self.act_instant.triggered.connect(self._trigger_capture)
        self.act_initial.triggered.connect(lambda: self._trigger_capture(-1))

        self.act_delay_3s.triggered.connect(lambda: self._trigger_capture(3))
        self.act_delay_5s.triggered.connect(lambda: self._trigger_capture(5))
        self.act_delay_10s.triggered.connect(lambda: self._trigger_capture(10))
