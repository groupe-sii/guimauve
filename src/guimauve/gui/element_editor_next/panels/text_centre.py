"""Centre of a text variant: the text it looks for."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import TextFindField
from guimauve.gui.element_editor_next.state import Store
from guimauve.gui.element_editor_next.theme import ThemeManager
from guimauve.models.variant import TextVariant

UNDO_LABEL = "Text"


class TextCentre(QWidget):
    """Text of the selected text variant, set in the store as it is typed; hidden for any other selection.

    An edit, from its first key to Enter or the focus leaving the field, is one undo step; it ends with the text
    without its leading and trailing spaces. A text changed elsewhere, by an undo for instance, ends the edit.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._store = store
        self._key: int | None = None
        self._gesture: int | None = None
        self.field = TextFindField(theme)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.field)

        self.field.edited.connect(self._edit)
        self.field.edit_finished.connect(self._finish)
        store.selection_changed.connect(self.refresh)
        store.document_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        store = self._store
        key = store.selected_variant
        variant = None if key is None else store.document.get(key)
        self.setVisible(isinstance(variant, TextVariant))
        if not isinstance(variant, TextVariant):
            self._key, self._gesture = None, None
            return
        if key != self._key or variant.text != self.field.text():
            self._gesture = None  # another variant, or a text changed elsewhere: the edit ends
        self._key = key
        self.field.set_text(variant.text)
        issues = store.issues_of(key, "text")
        self.field.set_error(issues[0].message if issues else None)

    def _edit(self, text: str) -> None:
        if self._key is None:
            return
        if self._gesture is None:
            self._gesture = self._store.new_gesture()
        self._store.set_field(self._key, "text", text, UNDO_LABEL, self._gesture)

    def _finish(self) -> None:
        if self._key is not None:
            text = self._store.document.get(self._key).text
            if text != text.strip():
                if self._gesture is None:
                    self._gesture = self._store.new_gesture()
                self._store.set_field(self._key, "text", text.strip(), UNDO_LABEL, self._gesture)
        self._gesture = None
