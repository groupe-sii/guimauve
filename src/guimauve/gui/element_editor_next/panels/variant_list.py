"""Variant list: the variants of the element, in the order they are tried."""

from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QDrag, QDropEvent, QGuiApplication, QKeyEvent, QKeySequence, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.element_editor_next.components import (
    Button,
    CenteredLabel,
    IconButton,
    MenuButton,
    RowContent,
    Thumbnail,
    VariantKind,
    VariantRow,
    add_item,
    add_title,
    styled_menu,
)
from guimauve.gui.element_editor_next.schema import FIXED_POSITION_KEYS
from guimauve.gui.element_editor_next.schema.fields import no_fixed_position
from guimauve.gui.element_editor_next.services import IMAGE_FILTER, ThumbnailCache, read_image
from guimauve.gui.element_editor_next.state import Store, new_name, resolve
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager
from guimauve.models.variant import ImageVariant, TextVariant

COLLAPSED_KEY = "editor/variants_collapsed"
HINT = "Tried from top to bottom. Drag to reorder."
FIXED_NOTE = "Not used while a fixed position is set."
EMPTY_TITLE = "No variant yet"
EMPTY_TEXT = "Add what Guimauve should look for on screen."
EMPTY_FIXED = "No variant is needed with a fixed position."
NOT_YET = "Not available yet"
UNREADABLE = "This file is not an image Guimauve can read."

DUPLICATE = "Ctrl+D"
MOVE_UP = "Alt+Up"
MOVE_DOWN = "Alt+Down"
DELETE = QKeySequence.StandardKey.Delete
"""Shortcuts of the list, active while it has the focus; a key sequence is only built once the app runs."""

CAPTURES = (("Initial screen", Icon.MONITOR), ("Instant", Icon.CAMERA), ("After a delay…", Icon.TIMER))
"""Moments of a capture, available with the capture interface."""


def ask_image_file(parent: QWidget) -> Path | None:
    """Asks for an image file to import; None when cancelled."""
    path, _ = QFileDialog.getOpenFileName(parent, "Import an image", "", IMAGE_FILTER)
    return Path(path) if path else None


def warn(parent: QWidget, text: str) -> None:
    QMessageBox.warning(parent, "Import an image", text)


def drop_index(source: int, row: int, below: bool, count: int) -> int:
    """Position of a row dropped on another row, once removed from its own position.

    :param row: Row under the drop, or -1 below the last one.
    :param below: Dropped on the lower half of the row.
    """
    index = count if row < 0 else row + below
    return index - 1 if index > source else index


class _List(QListWidget):
    """List of the rows, with its shortcuts; a row dropped elsewhere is moved through the store, not by the list."""

    rename_requested = Signal()
    duplicate_requested = Signal()
    delete_requested = Signal()
    move_requested = Signal(int)
    """Move the current row by this offset."""
    dropped = Signal(int, int)
    """A row was dragged from the first position to the second one."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._from_grip = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Notes whether the press is on the grip of a row, the only place a drag starts from."""
        widget = self.viewport().childAt(event.position().toPoint())
        self._from_grip = widget is not None and widget.objectName() == "grip"
        super().mousePressEvent(event)

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        row = self.itemWidget(item) if item is not None else None
        if not self._from_grip or row is None:
            return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData([item]))
        drag.setPixmap(row.grab())
        drag.setHotSpot(row.mapFromGlobal(QCursor.pos()))
        QGuiApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            QGuiApplication.restoreOverrideCursor()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = QKeySequence(event.keyCombination())
        if event.key() == Qt.Key.Key_F2 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.rename_requested.emit()
        elif key == QKeySequence(DUPLICATE):
            self.duplicate_requested.emit()
        elif key == QKeySequence(MOVE_UP):
            self.move_requested.emit(-1)
        elif key == QKeySequence(MOVE_DOWN):
            self.move_requested.emit(1)
        elif event.matches(DELETE):
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        source = self.currentRow()
        target = self.indexAt(event.position().toPoint())
        below = self.dropIndicatorPosition() is QAbstractItemView.DropIndicatorPosition.BelowItem
        event.setDropAction(Qt.DropAction.IgnoreAction)  # the rows are rebuilt from the store
        event.accept()
        if source >= 0:
            self.dropped.emit(source, drop_index(source, target.row() if target.isValid() else -1, below, self.count()))


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

        self._add = self._add_button()
        self._duplicate = IconButton(Icon.COPY, theme, "Duplicate", QKeySequence(DUPLICATE))
        self._duplicate.clicked.connect(self._duplicate_current)
        self._up = IconButton(Icon.ARROW_UP, theme, "Move up", QKeySequence(MOVE_UP))
        self._up.clicked.connect(lambda: self._move_current(-1))
        self._down = IconButton(Icon.ARROW_DOWN, theme, "Move down", QKeySequence(MOVE_DOWN))
        self._down.clicked.connect(lambda: self._move_current(1))
        self._delete = IconButton(Icon.TRASH, theme, "Delete", QKeySequence(DELETE))
        self._delete.clicked.connect(self._delete_current)
        self._tools = QWidget()
        self._tools.setObjectName("tools")
        tools = QHBoxLayout(self._tools)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(METRICS.space(1) // 2)
        tools.addSpacing(METRICS.space(1))
        for button in (self._duplicate, self._up, self._down):
            tools.addWidget(button)
        tools.addStretch()
        tools.addWidget(self._delete)
        self._toolbar = QHBoxLayout()
        self._toolbar.setSpacing(0)
        self._toolbar.addWidget(self._add)
        self._toolbar.addWidget(self._tools, 1)

        self._list = _List()
        self._list.setObjectName("variantList")
        self._list.setSpacing(1)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)  # rows follow the width of the list
        self._list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.currentRowChanged.connect(self._select_row)
        self._list.itemDoubleClicked.connect(lambda item: self._rename(self._list.row(item)))
        self._list.rename_requested.connect(lambda: self._rename(self._list.currentRow()))
        self._list.duplicate_requested.connect(self._duplicate_current)
        self._list.delete_requested.connect(self._delete_current)
        self._list.move_requested.connect(self._move_current)
        self._list.dropped.connect(lambda source, index: self._store.move_variant(self._keys[source], index))

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
        capture = Button("Capture an image")
        capture.setMenu(self._image_menu(capture))
        find = Button("Find a text")
        find.clicked.connect(self.add_text)
        self._empty_layout.addWidget(capture)
        self._empty_layout.addWidget(find)

        self._note = QLabel(HINT)
        self._note.setObjectName("note")
        self._note.setProperty("muted", True)
        self._note.setWordWrap(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(METRICS.space(2), METRICS.space(3), METRICS.space(2), METRICS.space(3))
        self._layout.setSpacing(METRICS.space(2))
        self._layout.addLayout(self._header)
        self._layout.addLayout(self._toolbar)
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
        center = Qt.AlignmentFlag.AlignHCenter if collapsed else Qt.AlignmentFlag(0)
        self._header.setAlignment(self._toggle, center)
        self._toolbar.setAlignment(self._add, center)
        self._tools.setVisible(not collapsed)
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

    # Actions

    def add_text(self) -> None:
        """Adds a text variant, whose text is typed in the center of the window."""
        self._store.add_variant(TextVariant(name=self._new_name(), text=""))

    def import_image(self) -> None:
        """Adds an image variant from a file."""
        path = ask_image_file(self)
        if path is None:
            return
        image = read_image(path)
        if image is None:
            warn(self, UNREADABLE)
            return
        self._store.add_variant(ImageVariant(name=self._new_name(), image=image))

    def _new_name(self) -> str:
        return new_name([variant.name for variant in self._store.document.variants])

    def _current(self) -> int | None:
        selected = self._store.selected_variant
        return selected if selected in self._keys else None

    def _duplicate_current(self) -> None:
        if (key := self._current()) is not None:
            self._store.duplicate_variant(key)

    def _delete_current(self) -> None:
        if (key := self._current()) is not None:
            self._store.remove_variant(key)
            self._list.setFocus()

    def _move_current(self, offset: int) -> None:
        if (key := self._current()) is not None:
            self._store.move_variant(key, self._keys.index(key) + offset)

    def _update_buttons(self) -> None:
        key = self._current()
        index = -1 if key is None else self._keys.index(key)
        self._duplicate.setEnabled(key is not None)
        self._delete.setEnabled(key is not None)
        self._up.setEnabled(index > 0)
        self._down.setEnabled(0 <= index < len(self._keys) - 1)

    def _add_button(self) -> MenuButton:
        button = MenuButton(Icon.PLUS, self._theme, "Add a variant")
        button.setObjectName("add")
        button.setProperty("tinted", True)
        menu = self._image_menu(button)
        menu.addSeparator()
        add_item(menu, "Find a text", Icon.TYPE, self._theme).triggered.connect(self.add_text)
        button.setMenu(menu)
        return button

    def _image_menu(self, parent: QWidget) -> QMenu:
        """Ways to add an image variant: the captures, available with the capture interface, and a file."""
        menu = styled_menu(parent)
        add_title(menu, "Capture an image")
        for text, name in CAPTURES:
            add_item(menu, text, name, self._theme, enabled=False).setToolTip(NOT_YET)
        add_item(menu, "Import a file…", Icon.IMAGE_UP, self._theme).triggered.connect(self.import_image)
        return menu

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
        self._update_buttons()

    def _select_row(self, index: int) -> None:
        if 0 <= index < len(self._keys):
            self._store.select(self._keys[index])

    def _rename(self, index: int) -> None:
        rows = self.rows()
        if 0 <= index < len(rows):
            rows[index].start_rename()
