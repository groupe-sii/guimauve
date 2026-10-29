"""Panel of the results of the Test, under the canvas."""

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPersistentModelIndex, QRect, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QHideEvent, QPainter
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
from guimauve.gui.element_editor_next.components import (
    CenteredLabel,
    ElidedLabel,
    IconLabel,
    MatchPreview,
    text_icon_button,
)
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.overlays.test_session import TestViewSession
from guimauve.gui.element_editor_next.panels.results import (
    FOUND,
    NOT_FOUND,
    NOT_TESTED,
    SKIPPED,
    STALE,
    USED,
    Row,
    preview,
    rows,
    screen_views,
    summary,
)
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.state import Mode, Store, TestScope
from guimauve.gui.element_editor_next.system import ScreenMap
from guimauve.gui.element_editor_next.theme import METRICS, TYPE, Icon, Palette, ThemeManager

COLUMNS = ("#", "Variant", "Method", "Score", "Position", "Screen", "Status")
NUMBER, VARIANT, METHOD, SCORE, POSITION, SCREEN, STATUS = range(len(COLUMNS))
NUMERIC = (NUMBER, SCORE, POSITION, SCREEN)
"""Columns of numbers, in the fixed-width font of the system."""
UNDER_VARIANT = "\u2003match"
"""Variant column of a match of the element, set in under its variant."""
MATCH_ROLE = Qt.ItemDataRole.UserRole
"""Data of an item: the index of its match in the report, None for a variant."""
HOVER_DELAY_MS = 300
"""Time over a row before its preview opens; a row chosen with the keys opens it at once."""


class ResultsPanel(QFrame):
    """Summary of the last test and its matches, shown in Test mode only.

    A variant lists its matches; the element lists its variants with their matches under them, numbered as on the
    full screen. A result older than the last change stays, dimmed, until the next test. Resting the mouse on a
    match, or choosing it with the keys, previews it on the capture. Full screen, or a double click on a match,
    shows the result over the captures on the screens they come from.
    """

    def __init__(
        self, store: Store, theme: ThemeManager, screens: ScreenMap | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setObjectName("results")
        self._store, self._theme = store, theme
        self._screens = screens or ScreenMap([])
        self._session: TestViewSession | None = None

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
        self.tree.itemDoubleClicked.connect(lambda item: self.show_full_screen(item.data(NUMBER, MATCH_ROLE)))
        self.tree.setMouseTracking(True)
        self.tree.itemEntered.connect(self._hover)
        self.tree.currentItemChanged.connect(self._choose)
        self.tree.viewport().installEventFilter(self)
        self.preview = MatchPreview(theme, self)
        self._hovered: QTreeWidgetItem | None = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(HOVER_DELAY_MS)
        self._hover_timer.timeout.connect(lambda: self._show_preview(self._hovered))
        tabular(self.tree)

        top = QHBoxLayout()
        top.setSpacing(METRICS.space(2))
        top.addWidget(title)
        top.addWidget(self.summary, 1)
        top.addWidget(self.stale)
        self.full_screen = text_icon_button("Full screen", Icon.SCAN, theme)
        self.full_screen.setToolTip("Show the result on the captures, on their screens")
        self.full_screen.clicked.connect(lambda: self.show_full_screen())
        top.addWidget(self.full_screen)
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

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.tree.viewport() and event.type() == QEvent.Type.Leave:
            self._hide_preview()
        return super().eventFilter(watched, event)

    def hideEvent(self, event: QHideEvent) -> None:
        self._hide_preview()
        super().hideEvent(event)

    def refresh(self) -> None:
        self._hide_preview()
        with QSignalBlocker(self.tree):  # a new current row is not a row chosen with the keys
            self._fill()

    def _fill(self) -> None:
        store = self._store
        self.setVisible(store.mode is Mode.TEST)
        result = store.test_result
        self.empty.setVisible(result is None)
        self.tree.clear()
        if result is None:
            for widget in (self.summary, self.stale, self.full_screen, self._error_row, self._warning_row, self.tree):
                widget.setVisible(False)
            return

        said = summary(result)
        self.full_screen.setVisible(bool(result.captures) and result.report is not None)
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

    # Full screen

    def show_full_screen(self, focused: int | None = None) -> None:
        """Shows the result over the captures, on their screens, the focused match with a halo."""
        result = self._store.test_result
        if result is None or result.report is None or not result.captures or self._session is not None:
            return
        self._hide_preview()
        code = self._store.document.code_overrides.get("search_area")
        title = f"Test result · {summary(result).text}"
        self._session = TestViewSession(screen_views(result, code), self._screens, title, focused, self)
        self._session.finished.connect(self._full_screen_closed)
        self._session.start()

    @property
    def session(self) -> TestViewSession | None:
        """The full screen while it shows."""
        return self._session

    def _full_screen_closed(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.deleteLater()

    # Preview

    def _hover(self, item: QTreeWidgetItem) -> None:
        self._hovered = item
        self.preview.hide()
        self._hover_timer.start()

    def _choose(self, item: QTreeWidgetItem | None) -> None:
        if item is not None and self.tree.hasFocus():  # with the keys, not by the refresh of the table
            self._show_preview(item)

    def _show_preview(self, item: QTreeWidgetItem | None) -> None:
        result = self._store.test_result
        match = None if item is None else item.data(NUMBER, MATCH_ROLE)
        least = (METRICS.preview_min_width, METRICS.preview_min_height)
        shown = None if result is None or match is None else preview(result, match, METRICS.preview_context, least)
        if item is None or shown is None:
            self.preview.hide()
            return
        self.preview.show_match(
            to_qimage(shown.image), list(shown.box), shown.target, shown.used, _row_rect(self.tree, item)
        )

    def _hide_preview(self) -> None:
        self._hover_timer.stop()
        self._hovered = None
        self.preview.hide()


def _row_rect(tree: QTreeWidget, item: QTreeWidgetItem) -> QRect:
    """Row of an item, across the table, in global coordinates."""
    viewport = tree.viewport()
    row = tree.visualItemRect(item)
    row.setLeft(0)
    row.setWidth(viewport.width())
    return QRect(viewport.mapToGlobal(row.topLeft()), row.size())


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
