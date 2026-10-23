"""Variant tab of the inspector: the selected variant, its targets, its match area and its overrides."""

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.element_editor_next.components import Button, CenteredLabel, FormRow, IconButton, LabelColumn, Variant
from guimauve.gui.element_editor_next.panels.field_binding import FieldBinding
from guimauve.gui.element_editor_next.schema import FIELDS, FieldDescriptor, override_groups
from guimauve.gui.element_editor_next.state import Source, Store, resolve
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager
from guimauve.models.variant import ImageVariant, TextVariant

IMAGE_CENTER = "Image center"
NO_TARGET = "Targets are added on the image."
WHOLE_IMAGE = "Whole image"
MATCH_AREA_NOTE = "Only this part of the image is compared; it is drawn on the image."
OVERRIDES_NOTE = "These values replace the element settings when this variant is tried."
UNNAMED = "Unnamed"


class _TargetRow(QFrame):
    """Number, editable name, coordinates and delete button of one target; highlighted while selected.

    A click on the row or the focus in its name selects the target, as on the image.
    """

    activated = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("targetRow", True)
        self.setProperty("selected", False)
        self.number = CenteredLabel()
        self.number.setProperty("rowNumber", True)
        self.number.setFixedWidth(METRICS.space(3))
        self.name = QLineEdit()
        self.name.setPlaceholderText(UNNAMED)
        self.name.installEventFilter(self)
        self.position = CenteredLabel()
        self.position.setProperty("muted", True)
        self.delete = IconButton(Icon.X, theme, "Delete target")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(2), 2, METRICS.space(1), 2)
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self.number)
        layout.addWidget(self.name, 1)
        layout.addWidget(self.position)
        layout.addWidget(self.delete)

    def set_selected(self, selected: bool) -> None:
        if self.property("selected") != selected:
            self.setProperty("selected", selected)
            for widget in (self, self.number):
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.activated.emit()
        super().mousePressEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.name and event.type() == QEvent.Type.FocusIn:
            self.activated.emit()
        return super().eventFilter(watched, event)


class VariantInspector(QScrollArea):
    """Variant tab: what only a variant has, then the element settings it overrides.

    An override is added one at a time with "Override a setting", which copies the inherited value onto the
    variant; its reset removes it. Timeout, find all, screen and the fixed position stay on the element. The
    targets and the match area are created on the image; here they are renamed, removed or reset.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._store, self._theme = store, theme
        self._key: int | None = None
        self._target_keys: list[int] = []
        self._override_keys: list[str] = []
        self._bindings: list[FieldBinding] = []
        self._labels = LabelColumn(self.viewport(), self)

        self._name = QLineEdit()
        self._name.setObjectName("name")
        self._name.editingFinished.connect(self._rename)
        self._kind = QLabel()
        self._kind.setObjectName("kind")
        self._kind.setProperty("muted", True)

        self._image = QWidget()  # targets, default target and match area: image variants only
        self._targets = QVBoxLayout()
        self._targets.setSpacing(METRICS.space(1))
        self._no_target = QLabel(NO_TARGET)
        self._no_target.setProperty("muted", True)
        self._default_target = QComboBox()
        self._default_target.setObjectName("defaultTarget")
        self._default_target.activated.connect(self._choose_default_target)
        self._match_area = QLabel()
        self._match_area.setObjectName("matchArea")
        self._match_area_reset = IconButton(Icon.ROTATE_CCW, theme, "Use the whole image")
        self._match_area_reset.setObjectName("resetMatchArea")
        self._match_area_reset.clicked.connect(self._reset_match_area)
        image = QVBoxLayout(self._image)
        image.setContentsMargins(0, 0, 0, 0)
        image.setSpacing(METRICS.space(2))
        image.addWidget(_heading("Targets"))
        image.addLayout(self._targets)
        image.addWidget(self._no_target)
        image.addWidget(self._form_row("Default target", self._default_target))
        image.addSpacing(METRICS.space(2))
        area = QHBoxLayout()
        area.addWidget(self._match_area, 1)
        area.addWidget(self._match_area_reset)
        image.addWidget(_heading("Match area"))
        image.addLayout(area)
        image.addWidget(_note(MATCH_AREA_NOTE))

        self._overrides = QVBoxLayout()
        self._overrides.setSpacing(METRICS.space(2))
        self._override = Button("Override a setting", Variant.GHOST)
        self._override.setObjectName("override")
        self._override.setIcon(theme.icon(Icon.PLUS))
        theme.changed.connect(lambda: self._override.setIcon(theme.icon(Icon.PLUS)))
        menu = QMenu(self._override)
        menu.aboutToShow.connect(lambda: self._fill_override_menu(menu))
        self._override.setMenu(menu)

        self._content = content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(METRICS.space(4), METRICS.space(3), METRICS.space(4), METRICS.space(4))
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self._form_row("Name", self._name))
        layout.addWidget(self._kind)
        layout.addSpacing(METRICS.space(2))
        layout.addWidget(self._image)
        layout.addSpacing(METRICS.space(2))
        layout.addWidget(_heading("Overrides"))
        layout.addWidget(_note(OVERRIDES_NOTE))
        layout.addLayout(self._overrides)
        layout.addWidget(self._override, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        store.document_changed.connect(self.refresh)
        store.selection_changed.connect(self.refresh)
        store.mode_changed.connect(self.refresh)
        self.refresh()

    # Refresh

    def refresh(self) -> None:
        store = self._store
        key = store.selected_variant
        self._content.setVisible(key is not None)
        if key is None:
            self._key = None
            return
        if key != self._key:
            self._key, self._target_keys, self._override_keys = key, [], []
        variant = store.document.get(key)

        if not self._name.hasFocus():
            self._name.setText(variant.name)
        self._kind.setText(_kind(variant))
        self._image.setVisible(isinstance(variant, ImageVariant))
        if isinstance(variant, ImageVariant):
            self._show_targets(key, variant)
            self._show_match_area(variant)
        self._show_overrides(key)

    def _show_targets(self, key: int, variant: ImageVariant) -> None:
        targets = variant.targets or []
        keys = [self._store.document.key(target) for target in targets]
        if keys != self._target_keys:
            _clear(self._targets)
            for target_key in keys:
                row = _TargetRow(self._theme)
                row.name.editingFinished.connect(lambda row=row, t=target_key: self._rename_target(t, row.name.text()))
                row.delete.clicked.connect(lambda _=False, t=target_key: self._store.remove_target(key, t))
                row.activated.connect(lambda t=target_key: self._store.select(key, t))
                self._targets.addWidget(row)
            self._target_keys = keys
        items = (self._targets.itemAt(index) for index in range(self._targets.count()))
        rows = [widget for item in items if item is not None and isinstance(widget := item.widget(), _TargetRow)]
        for number, (row, target) in enumerate(zip(rows, targets, strict=True), start=1):
            row.number.setText(str(number))
            if not row.name.hasFocus():
                row.name.setText(target.name or "")
            row.position.setText(f"{target.x}, {target.y}")
            row.set_selected(self._store.document.key(target) == self._store.selected_target)
        self._no_target.setVisible(not targets)

        names = [target.name for target in targets if target.name]
        self._default_target.blockSignals(True)
        self._default_target.clear()
        self._default_target.addItem(IMAGE_CENTER, None)
        for name in names:
            self._default_target.addItem(name, name)
        current = variant.default_target
        if current is not None and current not in names:  # a name left over in the file: shown, to be changed
            self._default_target.addItem(current, current)
        self._default_target.setCurrentIndex(self._default_target.findData(current) if current is not None else 0)
        self._default_target.blockSignals(False)

    def _show_match_area(self, variant: ImageVariant) -> None:
        area = variant.match_area
        if area is None:
            self._match_area.setText(WHOLE_IMAGE)
        else:
            self._match_area.setText(
                f"{area.left}, {area.top} to {area.right}, {area.bottom} · {area.width} × {area.height}"
            )
        self._match_area_reset.setVisible(area is not None)

    def _show_overrides(self, key: int) -> None:
        store = self._store
        variant = store.document.get(key)
        groups = override_groups(type(variant))
        own = [
            field
            for _, fields in groups
            for field in fields
            if {Source.VARIANT, Source.VARIANT_TRIAL}
            & resolve(field.key, store.document, store.default, variant).layers.keys()
        ]
        keys = [field.key for field in own]
        if keys != self._override_keys:
            _clear(self._overrides)
            self._bindings = []
            for title, fields in groups:
                shown = [field for field in fields if field in own]
                if not shown:
                    continue
                self._overrides.addWidget(_subheading(title))
                for field in shown:
                    binding = FieldBinding(store, field, self._theme, owner=key)
                    self._bindings.append(binding)
                    self._labels.add(binding.field)
                    self._overrides.addWidget(binding.field)
            self._override_keys = keys

        values = {
            k: resolve(k, store.document, store.default, variant, include_code=store.include_code).value for k in FIELDS
        }
        for binding in self._bindings:
            binding.refresh(values)
            binding.field.setVisible(True)  # an override stays visible, even for a method turned off

    def _form_row(self, label: str, widget: QWidget) -> FormRow:
        row = FormRow(label, widget)
        self._labels.add(row)
        return row

    # Edits

    def _rename(self) -> None:
        """Renames the variant; the field shows the name kept, normalized or put back when refused."""
        if self._key is None:
            return
        self._store.rename_variant(self._key, self._name.text())
        self._name.setText(self._store.document.get(self._key).name)

    def _rename_target(self, target: int, name: str) -> None:
        if self._key is not None:
            self._store.rename_target(self._key, target, name.strip() or None)

    def _choose_default_target(self, index: int) -> None:
        if self._key is not None:
            self._store.set_field(self._key, "default_target", self._default_target.itemData(index), "Default target")

    def _reset_match_area(self) -> None:
        if self._key is not None:
            self._store.set_field(self._key, "match_area", None, "Match area")

    def _fill_override_menu(self, menu: QMenu) -> None:
        """Settings not overridden yet, grouped as in the tab."""
        menu.clear()
        if self._key is None:
            return
        variant = self._store.document.get(self._key)
        for title, fields in override_groups(type(variant)):
            free = [field for field in fields if field.key not in self._override_keys]
            if not free:
                continue
            menu.addSection(title)
            for field in free:
                menu.addAction(self._override_action(menu, field))

    def _override_action(self, menu: QMenu, field: FieldDescriptor) -> QAction:
        action = QAction(field.label, menu)
        key = self._key
        assert key is not None
        action.triggered.connect(lambda: self._store.override(key, field.key, field.label))
        return action


def _kind(variant) -> str:  # type: ignore[no-untyped-def]  # an image or a text variant
    if isinstance(variant, ImageVariant):
        if variant.image is None:
            return "Image, not captured yet"
        height, width = variant.image.shape[:2]
        return f"Image · {width} × {height} px"
    text = variant.text if isinstance(variant, TextVariant) else ""
    return f"Text · “{text}”" if text else "Text, not typed yet"


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("sectionTitle", True)
    return label


def _subheading(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("fieldLabel", True)
    label.setObjectName("group")
    return label


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", True)
    label.setWordWrap(True)
    return label


def _clear(layout: QVBoxLayout) -> None:
    while (item := layout.takeAt(0)) is not None:
        if (widget := item.widget()) is not None:
            widget.hide()
            widget.deleteLater()
