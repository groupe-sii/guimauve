"""Variant list: the variants of the element, in the order they are tried."""

from PySide6.QtCore import QSettings, QSize, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.element_editor_next.components import (
    CenteredLabel,
    IconButton,
    RowContent,
    Thumbnail,
    VariantKind,
    VariantRow,
)
from guimauve.gui.element_editor_next.schema import FIXED_POSITION_KEYS
from guimauve.gui.element_editor_next.schema.fields import no_fixed_position
from guimauve.gui.element_editor_next.services import ThumbnailCache
from guimauve.gui.element_editor_next.state import Store, resolve
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager
from guimauve.models.variant import ImageVariant, TextVariant

COLLAPSED_KEY = "editor/variants_collapsed"
HINT = "Tried from top to bottom."
FIXED_NOTE = "Not used while a fixed position is set."
EMPTY_TITLE = "No variant yet"
EMPTY_TEXT = "Add what Guimauve should look for on screen."
EMPTY_FIXED = "No variant is needed with a fixed position."


class _List(QListWidget):
    """List of the rows; F2 asks to rename the current one."""

    rename_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F2 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.rename_requested.emit()
            return
        super().keyPressEvent(event)


class VariantList(QFrame):
    """Left panel: one row per variant, the selection, and the renaming.

    The panel collapses into a column of numbers and thumbnails; its state is kept for the next sessions. While a
    fixed position is set, the variants are not used: their rows are faded, with a note.

    :param settings: Where the collapsed state is kept.
    """

    def __init__(self, store: Store, theme: ThemeManager, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("variants")
        self.setProperty("pane", "side")
        self._store, self._theme, self._settings = store, theme, settings
        self._collapsed = bool(settings.value(COLLAPSED_KEY, False, type=bool))
        self._keys: list[int] = []
        self._shown_collapsed = self._collapsed
        self._thumbnails = {
            False: ThumbnailCache(Thumbnail.box(QSize(METRICS.thumbnail_width, METRICS.thumbnail_height))),
            True: ThumbnailCache(Thumbnail.box(QSize(METRICS.thumbnail_small_width, METRICS.thumbnail_small_height))),
        }

        self._title = CenteredLabel("Variants")
        self._title.setProperty("panelTitle", True)
        self._toggle = IconButton(Icon.PANEL_LEFT_CLOSE, theme, "Collapse panel")
        self._toggle.setObjectName("toggle")
        self._toggle.clicked.connect(lambda: self.set_collapsed(not self._collapsed))
        self._header = QHBoxLayout()
        self._header.setSpacing(METRICS.space(1))
        self._header.addWidget(self._title, 1)
        self._header.addWidget(self._toggle)

        self._list = _List()
        self._list.setObjectName("variantList")
        self._list.setSpacing(1)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)  # rows follow the width of the list
        self._list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.currentRowChanged.connect(self._select_row)
        self._list.itemDoubleClicked.connect(lambda item: self._rename(self._list.row(item)))
        self._list.rename_requested.connect(lambda: self._rename(self._list.currentRow()))

        self._empty = QWidget()
        self._empty.setObjectName("empty")
        empty_title = QLabel(EMPTY_TITLE)
        empty_title.setProperty("emptyTitle", True)
        self._empty_text = QLabel(EMPTY_TEXT)
        self._empty_text.setProperty("muted", True)
        self._empty_text.setWordWrap(True)
        self._empty_layout = QVBoxLayout(self._empty)
        self._empty_layout.setContentsMargins(METRICS.space(2), METRICS.space(6), METRICS.space(2), 0)
        self._empty_layout.setSpacing(METRICS.space(2))
        for label in (empty_title, self._empty_text):
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._empty_layout.addWidget(label)

        self._note = QLabel(HINT)
        self._note.setObjectName("note")
        self._note.setProperty("muted", True)
        self._note.setWordWrap(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(METRICS.space(2), METRICS.space(3), METRICS.space(2), METRICS.space(3))
        self._layout.setSpacing(METRICS.space(2))
        self._layout.addLayout(self._header)
        self._layout.addWidget(self._list, 1)
        self._layout.addWidget(self._empty)
        self._layout.addStretch()
        self._layout.addWidget(self._note)

        store.document_changed.connect(self.refresh)
        store.mode_changed.connect(self.refresh)  # include_code changes the fixed position
        store.selection_changed.connect(self._show_selection)
        self.set_collapsed(self._collapsed)

    # State

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        """Collapses or expands the panel and keeps the choice."""
        if collapsed != bool(self._settings.value(COLLAPSED_KEY, False, type=bool)):
            self._settings.setValue(COLLAPSED_KEY, collapsed)
        self._collapsed = collapsed
        self.setFixedWidth(METRICS.variants_collapsed_width if collapsed else METRICS.variants_width)
        self._title.setVisible(not collapsed)
        self._toggle.set_icon(Icon.PANEL_LEFT_OPEN if collapsed else Icon.PANEL_LEFT_CLOSE)
        self._toggle.setToolTip("Expand panel" if collapsed else "Collapse panel")
        self._header.setAlignment(self._toggle, Qt.AlignmentFlag.AlignHCenter if collapsed else Qt.AlignmentFlag(0))
        margin = METRICS.space(1) if collapsed else METRICS.space(2)
        self._layout.setContentsMargins(margin, METRICS.space(3), margin, METRICS.space(3))
        self.refresh()

    def rows(self) -> list[VariantRow]:
        """Rows in display order."""
        rows = [self._list.itemWidget(self._list.item(index)) for index in range(self._list.count())]
        return [row for row in rows if isinstance(row, VariantRow)]

    # Refresh

    def refresh(self) -> None:
        store = self._store
        keys = store.variant_keys()
        if keys != self._keys or self._collapsed != self._shown_collapsed:
            self._rebuild(keys)
        fixed = not no_fixed_position(
            {
                k: resolve(k, store.document, store.default, include_code=store.include_code).value
                for k in FIXED_POSITION_KEYS
            }
        )
        for row, key in zip(self.rows(), keys, strict=True):
            row.set_content(self._content(key, keys.index(key) + 1, fixed))
        self._thumbnails[self._collapsed].keep(set(keys))

        self._list.setVisible(bool(keys))
        self._empty.setVisible(not keys and not self._collapsed)
        self._empty_text.setText(EMPTY_FIXED if fixed else EMPTY_TEXT)
        self._note.setText(FIXED_NOTE if fixed else HINT)
        self._note.setVisible(bool(keys) and not self._collapsed)
        self._show_selection()

    def _rebuild(self, keys: list[int]) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for key in keys:
            row = VariantRow(self._theme, self._collapsed)
            row.renamed.connect(lambda name, key=key: self._store.rename_variant(key, name))
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, row.sizeHint().height()))  # the width follows the list
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
        self._list.blockSignals(False)
        self._keys, self._shown_collapsed = list(keys), self._collapsed

    def _content(self, key: int, number: int, dimmed: bool) -> RowContent:
        variant = self._store.document.get(key)
        summary = self._store.variant_summary(key)
        if isinstance(variant, ImageVariant):
            image = self._thumbnails[self._collapsed].get(key, variant, self.devicePixelRatioF())
            return RowContent(number, variant.name, VariantKind.IMAGE, image, summary=summary, dimmed=dimmed)
        text = variant.text if isinstance(variant, TextVariant) else ""
        return RowContent(number, variant.name, VariantKind.TEXT, text=text, summary=summary, dimmed=dimmed)

    # Selection

    def _show_selection(self) -> None:
        selected = self._store.selected_variant
        index = self._keys.index(selected) if selected in self._keys else -1
        self._list.blockSignals(True)
        self._list.setCurrentRow(index)
        self._list.blockSignals(False)
        for position, row in enumerate(self.rows()):
            row.set_selected(position == index)

    def _select_row(self, index: int) -> None:
        if 0 <= index < len(self._keys):
            self._store.select(self._keys[index])

    def _rename(self, index: int) -> None:
        rows = self.rows()
        if 0 <= index < len(rows):
            rows[index].start_rename()
