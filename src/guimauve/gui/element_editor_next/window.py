"""Window of the editor: the panels assembled, and how the session ends."""

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QSplitter, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.contract import Context, EditorResult
from guimauve.gui.element_editor_next.panels import (
    AlertBanner,
    CanvasPanel,
    CaptureFlow,
    Header,
    InspectorPanel,
    ScreenPicker,
    TestFlow,
    VariantList,
)
from guimauve.gui.element_editor_next.panels.header import REDO, SAVE, TEST, UNDO
from guimauve.gui.element_editor_next.services import CaptureService, TestRunner
from guimauve.gui.element_editor_next.state import Mode, Store
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

TITLE = "{name} – Guimauve"
VARIANTS_WIDTH_KEY = "editor/variants_width"
INSPECTOR_WIDTH_KEY = "editor/inspector_width"


class EditorWindow(QWidget):
    """Header, alert banner, then the variants, the canvas and the inspector side by side.

    The side panels are resized by dragging their edge, within the bounds of the metrics; their widths are kept for
    the next sessions. Save closes with the edited element, Skip or Cancel without it; closing the window means
    Skip, after a confirmation when the element was modified. The result is read once finished is emitted.

    The Test runs on the captures of the capture service, through the flow kept in test; a search still running when
    the window closes is stopped and waited for.
    """

    finished = Signal()
    """The window closed; result is set."""

    def __init__(
        self,
        store: Store,
        theme: ThemeManager,
        settings: QSettings,
        context: Context,
        capture: CaptureService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._store = store
        self.result: EditorResult | None = None
        self.setWindowTitle(TITLE.format(name=context.element.name))
        self.resize(1280, 800)

        self._header = Header(store, theme, settings, context.from_run)
        self._header.save_requested.connect(self._save)
        self._header.skip_requested.connect(self._skip)
        alert = AlertBanner(context.message, context.action, theme)

        self._settings = settings
        self.capture = CaptureFlow(store, capture, settings, self)
        self._runner = TestRunner(context.mouse_position, self)
        self.test = TestFlow(store, capture, self._runner, settings, self)
        self._variants = VariantList(store, theme, settings, self.capture)
        self._variants.collapsed_changed.connect(self._show_variants)
        canvas = CanvasPanel(store, theme, self.capture)
        inspector = InspectorPanel(store, theme, ScreenPicker(capture, self))
        inspector.setMinimumWidth(METRICS.inspector_min_width)
        inspector.setMaximumWidth(METRICS.inspector_max_width)

        self._body = QSplitter(Qt.Orientation.Horizontal)
        self._body.setObjectName("body")
        self._body.setChildrenCollapsible(False)
        self._body.setHandleWidth(METRICS.space(1))
        for widget in (self._variants, canvas, inspector):
            self._body.addWidget(widget)
        self._body.setStretchFactor(1, 1)
        self._body.splitterMoved.connect(self._keep_widths)
        self._show_variants(self._variants.is_collapsed())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(alert)
        layout.addWidget(self._body, 1)

        QShortcut(QKeySequence(SAVE), self, self._save)
        QShortcut(QKeySequence(UNDO), self, store.undo)
        QShortcut(QKeySequence(REDO), self, store.redo)
        QShortcut(QKeySequence(TEST), self, self._test)

    # Side panels

    def panel_widths(self) -> tuple[int, int]:
        """Widths of the variant list and the inspector."""
        sizes = self._body.sizes()
        return sizes[0], sizes[2]

    def _show_variants(self, collapsed: bool) -> None:
        """Sizes the panels, the list collapsed or at its kept width; a collapsed list cannot be resized."""
        self._body.handle(1).setEnabled(not collapsed)
        variants = (
            METRICS.variants_collapsed_width if collapsed else self._width(VARIANTS_WIDTH_KEY, METRICS.variants_width)
        )
        inspector = self._width(INSPECTOR_WIDTH_KEY, METRICS.inspector_width)
        total = max(sum(self._body.sizes()), self.width())
        self._body.setSizes([variants, total - variants - inspector, inspector])

    def _keep_widths(self) -> None:
        variants, inspector = self.panel_widths()
        if not self._variants.is_collapsed():
            self._settings.setValue(VARIANTS_WIDTH_KEY, variants)
        self._settings.setValue(INSPECTOR_WIDTH_KEY, inspector)

    def _width(self, key: str, default: int) -> int:
        value = self._settings.value(key, default, type=int)
        return value if isinstance(value, int) and value > 0 else default

    # Session

    def _test(self) -> None:
        """F5: switches to Test if needed, then asks to run it."""
        self._store.set_mode(Mode.TEST)
        self._store.request_test()

    def _save(self) -> None:
        if self._store.can_save:
            self._finish(EditorResult(self._store.result(), self._header.resume_mode))

    def _skip(self) -> None:
        self._finish(EditorResult(None, self._header.resume_mode))

    def _finish(self, result: EditorResult) -> None:
        self.result = result
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.result is None:  # closed by the window manager: Skip, once confirmed
            if self._store.is_modified and not self.confirm_discard():
                event.ignore()
                return
            self.result = EditorResult(None, self._header.resume_mode)
        self._runner.shutdown()  # a search still running ends before its thread goes
        event.accept()
        self.finished.emit()

    def confirm_discard(self) -> bool:
        """Asks whether to close without saving the changes."""
        box = self.discard_box()
        box.exec()
        clicked = box.clickedButton()
        return clicked is not None and box.buttonRole(clicked) is QMessageBox.ButtonRole.DestructiveRole

    def discard_box(self) -> QMessageBox:
        """Confirmation owned by the window, so it shows above it although the window stays on top."""
        box = QMessageBox(
            QMessageBox.Icon.Question, "Discard changes?", "The changes to this element are not saved.", parent=self
        )
        box.setWindowModality(Qt.WindowModality.WindowModal)
        box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        keep = box.addButton("Keep editing", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(keep)
        return box
