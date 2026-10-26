"""Right panel: the Element and Variant tabs of the inspector."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.panels.inspector import Inspector
from guimauve.gui.element_editor_next.panels.screen_picker import ScreenPicker
from guimauve.gui.element_editor_next.panels.variant_inspector import VariantInspector
from guimauve.gui.element_editor_next.state import Store
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

ELEMENT_TAB = 0
VARIANT_TAB = 1


class InspectorPanel(QFrame):
    """Tab bar Element / Variant above the two tabs.

    The Variant tab shows the variant selected in the list, named in its first field; it is disabled without
    variant. The tab only changes when the user picks it, not when the selection changes.
    """

    def __init__(
        self, store: Store, theme: ThemeManager, picker: ScreenPicker | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setObjectName("inspector")
        self._store = store

        self._element_tab = _tab("Element")
        self._variant_tab = _tab("Variant")
        self._group = QButtonGroup(self)
        self._group.addButton(self._element_tab, ELEMENT_TAB)
        self._group.addButton(self._variant_tab, VARIANT_TAB)
        self._group.idClicked.connect(self.set_tab)
        bar = QFrame()
        bar.setObjectName("tabs")
        tabs = QHBoxLayout(bar)
        tabs.setContentsMargins(METRICS.space(3), 0, METRICS.space(3), 0)
        tabs.setSpacing(METRICS.space(3))
        tabs.addWidget(self._element_tab)
        tabs.addWidget(self._variant_tab, 0)
        tabs.addStretch()

        self.element = Inspector(store, theme, picker)
        self.variant = VariantInspector(store, theme, picker)
        self._stack = QStackedWidget()
        self._stack.addWidget(self.element)
        self._stack.addWidget(self.variant)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(bar)
        layout.addWidget(self._stack, 1)

        store.document_changed.connect(self._refresh)  # the last variant can go
        store.selection_changed.connect(self._refresh)
        self.set_tab(ELEMENT_TAB)
        self._refresh()

    def tab(self) -> int:
        return self._stack.currentIndex()

    def set_tab(self, tab: int) -> None:
        self._stack.setCurrentIndex(tab)
        self._group.button(tab).setChecked(True)

    def _refresh(self) -> None:
        has_variant = self._store.selected_variant is not None
        self._variant_tab.setEnabled(has_variant)
        if not has_variant and self.tab() == VARIANT_TAB:
            self.set_tab(ELEMENT_TAB)


def _tab(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("tab", True)
    button.setCheckable(True)
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return button
