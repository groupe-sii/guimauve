"""Panel of the results of the Test, under the canvas."""

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.element_editor_next.canvas.status_bar import tabular
from guimauve.gui.element_editor_next.components import CenteredLabel, ElidedLabel, IconLabel
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.panels.results import (
    FOUND,
    NOT_FOUND,
    NOT_TESTED,
    SKIPPED,
    STALE,
    USED,
    Row,
    rows,
    summary,
)
from guimauve.gui.element_editor_next.state import Mode, Store, TestScope
from guimauve.gui.element_editor_next.theme import METRICS, TYPE, Icon, Palette, ThemeManager

COLUMNS = ("#", "Variant", "Method", "Score", "Position", "Screen", "Status")
NUMBER, VARIANT, METHOD, SCORE, POSITION, SCREEN, STATUS = range(len(COLUMNS))
NUMERIC = (NUMBER, SCORE, POSITION, SCREEN)
"""Columns of numbers, in the fixed-width font of the system."""
UNDER_VARIANT = "\u2003match"
"""Variant column of a match of the element, set in under its variant."""
MATCH_ROLE = Qt.ItemDataRole.UserRole
"""Data of an item: the index of its match in the report, None for a variant."""


class ResultsPanel(QFrame):
    """Summary of the last test and its matches, shown in Test mode only.

    A variant lists its matches; the element lists its variants with their matches under them, numbered as on the
    full screen. A result older than the last change stays, dimmed, until the next test.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("results")
        self._store, self._theme = store, theme

        title = CenteredLabel("Results")
        title.setProperty("sectionTitle", True)
        self.summary = ElidedLabel()
        self.stale = CenteredLabel(STALE)
        self.stale.setProperty("muted", True)
        self.error = ElidedLabel()
        self.error.setProperty("message", "error")
        self._error_row = _row(IconLabel(Icon.CIRCLE_ALERT, theme, "error"), self.error)
        self.warning = ElidedLabel()
        self._warning_row = _row(IconLabel(Icon.TRIANGLE_ALERT, theme, "warning"), self.warning)
        self.empty = QLabel(NOT_TESTED)
        self.empty.setProperty("muted", True)
        self.empty.setWordWrap(True)

        self.tree = QTreeWidget()
        self.tree.setObjectName("matches")
        self.tree.setColumnCount(len(COLUMNS))
        self.tree.setHeaderLabels(list(COLUMNS))
        self.tree.setRootIsDecorated(False)  # the matches of a variant always show, under it
        self.tree.setIndentation(0)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        header = self.tree.header()
        header.setHighlightSections(False)
        header.setSectionsClickable(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setStretchLastSection(True)
        self.tree.setItemDelegate(_Tinted(self.tree))
        tabular(self.tree)

        top = QHBoxLayout()
        top.setSpacing(METRICS.space(2))
        top.addWidget(title)
        top.addWidget(self.summary, 1)
        top.addWidget(self.stale)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(METRICS.space(3), METRICS.space(2), METRICS.space(3), METRICS.space(2))
        layout.setSpacing(METRICS.space(1))
        layout.addLayout(top)
        layout.addWidget(self._error_row)
        layout.addWidget(self._warning_row)
        layout.addWidget(self.empty)
        layout.addWidget(self.tree, 1)
        layout.addStretch()  # without the table, the summary stays at the top

        store.test_changed.connect(self.refresh)
        store.mode_changed.connect(self.refresh)
        theme.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        store = self._store
        self.setVisible(store.mode is Mode.TEST)
        result = store.test_result
        self.empty.setVisible(result is None)
        self.tree.clear()
        if result is None:
            for widget in (self.summary, self.stale, self._error_row, self._warning_row, self.tree):
                widget.setVisible(False)
            return

        said = summary(result)
        self.summary.setVisible(True)
        self.summary.setText(said.text)
        self.stale.setVisible(store.test_stale)
        set_style_property(self.summary, "muted", store.test_stale)
        set_style_property(self.tree, "stale", store.test_stale)
        self.error.setText(said.error or "")
        self._error_row.setVisible(said.error is not None)
        self.warning.setText(" · ".join(said.warnings))
        self.warning.setToolTip("\n".join(said.warnings))
        self._warning_row.setVisible(bool(said.warnings))

        listed = rows(result)
        element = result.scope is TestScope.ELEMENT
        self.tree.setVisible(bool(listed))
        self.tree.setColumnHidden(VARIANT, not element)
        self.tree.setColumnHidden(SCREEN, not said.screens)
        palette = self._theme.palette
        for row in listed:
            item = _item(row, palette)
            self.tree.addTopLevelItem(item)
            item.addChildren([_item(child, palette, under_variant=True) for child in row.children])
        self.tree.expandAll()
        for column in range(len(COLUMNS)):
            self.tree.resizeColumnToContents(column)
            self.tree.setColumnWidth(column, self.tree.columnWidth(column) + METRICS.space(4))


def _item(row: Row, palette: Palette, under_variant: bool = False) -> QTreeWidgetItem:
    """Line of the table: the used match tinted, the status in its color, a variant not found or skipped muted."""
    item = QTreeWidgetItem()
    texts = {
        NUMBER: "" if row.number is None else str(row.number),
        VARIANT: UNDER_VARIANT if under_variant else row.variant,
        METHOD: row.method,
        SCORE: row.score,
        POSITION: row.position,
        SCREEN: row.screen,
        STATUS: row.status,
    }
    for column, text in texts.items():
        item.setText(column, text)
    item.setToolTip(SCORE, row.score_tip)
    item.setToolTip(STATUS, row.status_tip)
    item.setData(NUMBER, MATCH_ROLE, row.match)
    for column in NUMERIC:
        item.setFont(column, _numbers())
    muted = QBrush(QColor(palette.text_muted))
    if row.status in (NOT_FOUND, SKIPPED):
        for column in texts:
            item.setForeground(column, muted)
    if under_variant:
        item.setForeground(VARIANT, muted)
    if row.used:
        for column in texts:
            item.setBackground(column, QBrush(QColor(palette.accent_tint)))
    color = {USED: palette.accent, FOUND: palette.success}.get(row.status)
    if color is not None:
        item.setForeground(STATUS, QBrush(QColor(color)))
        font = item.font(STATUS)
        font.setBold(True)
        item.setFont(STATUS, font)
    if row.number is None:  # a variant of the element, named in bold when found
        font = item.font(VARIANT)
        font.setBold(row.status == FOUND)
        item.setFont(VARIANT, font)
    return item


def _numbers() -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPixelSize(TYPE.small)
    return font


class _Tinted(QStyledItemDelegate):
    """Paints the background of an item, which the style sheet of the items would otherwise ignore."""

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        brush = index.data(Qt.ItemDataRole.BackgroundRole)
        if isinstance(brush, QBrush):
            painter.fillRect(option.rect, brush)  # type: ignore[attr-defined]
        super().paint(painter, option, index)


def _row(icon: QWidget, text: QWidget) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(METRICS.space(1))
    layout.addWidget(icon)
    layout.addWidget(text, 1)
    return row
