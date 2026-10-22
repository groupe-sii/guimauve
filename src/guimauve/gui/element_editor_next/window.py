"""Window of the editor: the panels assembled, and how the session ends."""

from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.contract import Context, EditorResult
from guimauve.gui.element_editor_next.panels import AlertBanner, Header, InspectorPanel, VariantList
from guimauve.gui.element_editor_next.panels.header import REDO, SAVE, UNDO
from guimauve.gui.element_editor_next.state import Store
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

TITLE = "{name} – Guimauve"


class EditorWindow(QWidget):
    """Header, alert banner, then the variants, the canvas and the inspector side by side.

    Save closes with the edited element, Skip or Cancel without it; closing the window means Skip, after a
    confirmation when the element was modified. The result is read once finished is emitted.
    """

    finished = Signal()
    """The window closed; result is set."""

    def __init__(
        self, store: Store, theme: ThemeManager, settings: QSettings, context: Context, parent: QWidget | None = None
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

        variants = VariantList(store, theme, settings)
        canvas = _pane("Canvas", "center")
        inspector = InspectorPanel(store, theme)
        inspector.setFixedWidth(METRICS.inspector_width)

        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(variants)
        body.addWidget(canvas, 1)
        body.addWidget(inspector)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(alert)
        layout.addLayout(body, 1)

        QShortcut(QKeySequence(SAVE), self, self._save)
        QShortcut(QKeySequence(UNDO), self, store.undo)
        QShortcut(QKeySequence(REDO), self, store.redo)

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
        event.accept()
        self.finished.emit()

    def confirm_discard(self) -> bool:
        """Asks whether to close without saving the changes."""
        box = QMessageBox(QMessageBox.Icon.Question, "Discard changes?", "The changes to this element are not saved.")
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        keep = box.addButton("Keep editing", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(keep)
        box.exec()
        return box.clickedButton() is discard


def _pane(title: str, kind: str) -> QFrame:
    """Panel to come in a later step, showing only its title."""
    pane = QFrame()
    pane.setProperty("pane", kind)
    label = QLabel(title)
    label.setProperty("muted", True)
    layout = QVBoxLayout(pane)
    layout.setContentsMargins(METRICS.space(3), METRICS.space(3), METRICS.space(3), METRICS.space(3))
    layout.addWidget(label)
    layout.addStretch()
    return pane
