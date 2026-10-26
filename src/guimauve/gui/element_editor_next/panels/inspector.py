"""Inspector: the properties of the element, by section, generated from the schema."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import Button, Disclosure, LabelColumn, Section, text_icon_button
from guimauve.gui.element_editor_next.panels.field_binding import FieldBinding
from guimauve.gui.element_editor_next.panels.screen_picker import ScreenPicker
from guimauve.gui.element_editor_next.schema import FIELDS, SECTIONS, SectionDescriptor
from guimauve.gui.element_editor_next.state import ELEMENT, Store, resolve
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

ADVANCED = "Advanced"
NOTES = {"fixed_position": "An axis not set keeps the mouse position."}
PICK = "Pick on screen"


class _SectionView:
    """A section of the inspector with its fields, and its advanced group if any."""

    def __init__(
        self, store: Store, descriptor: SectionDescriptor, theme: ThemeManager, picker: ScreenPicker | None = None
    ):
        self.descriptor = descriptor
        self.section = Section(descriptor.title, theme)
        self.bindings = [FieldBinding(store, field, theme) for field in descriptor.fields]
        self.pick: Button | None = None
        self.advanced: Disclosure | None = None

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(2))
        for binding in self.bindings:
            if not binding.descriptor.advanced:
                layout.addWidget(binding.field)
                continue
            if self.advanced is None:  # the group takes the place of its first setting
                self.advanced = Disclosure(ADVANCED, theme)
                layout.addWidget(self.advanced)
            self.advanced.add(binding.field)
        if self.advanced is not None:
            self.advanced.set_count(sum(binding.descriptor.advanced for binding in self.bindings))
        if note := NOTES.get(descriptor.key):
            label = QLabel(note)
            label.setProperty("muted", True)
            label.setWordWrap(True)
            layout.addWidget(label)
        if descriptor.key == "fixed_position" and picker is not None:
            self.pick = text_icon_button(PICK, Icon.LOCATE, theme)
            self.pick.setObjectName("pickOnScreen")
            self.pick.clicked.connect(lambda: _pick_position(store, picker))
            layout.addWidget(self.pick, 0, Qt.AlignmentFlag.AlignLeft)
        self.section.set_content(body)


class Inspector(QScrollArea):
    """Element tab: every property by section, bound to the store.

    Sections are collapsed when they appear, with badges counting the values set here, the code values and the
    issues. A detection section is hidden until the element has a variant of its kind.
    """

    def __init__(
        self, store: Store, theme: ThemeManager, picker: ScreenPicker | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._store = store
        self._picker = picker
        self._views = [_SectionView(store, descriptor, theme, picker) for descriptor in SECTIONS]
        self._labels = LabelColumn(self.viewport(), self)
        for view in self._views:
            for binding in view.bindings:
                self._labels.add(binding.field)
        self._shown: dict[str, bool] = {}

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(METRICS.space(2), METRICS.space(2), METRICS.space(2), METRICS.space(2))
        layout.setSpacing(0)
        for view in self._views:
            layout.addWidget(view.section)
        layout.addStretch()
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # the fields fit the width
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        store.document_changed.connect(self.refresh)
        store.mode_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        store = self._store
        values = {
            key: resolve(key, store.document, store.default, include_code=store.include_code).value for key in FIELDS
        }
        variants = store.document.variants
        for view in self._views:
            kind = view.descriptor.variant_kind
            shown = kind is None or any(isinstance(variant, kind) for variant in variants)
            if shown and not self._shown.get(view.descriptor.key, False):
                view.section.set_open(False)  # collapsed whenever it appears
                if view.advanced is not None:
                    view.advanced.set_open(False)
            self._shown[view.descriptor.key] = shown
            view.section.setVisible(shown)

            states = [binding.refresh(values) for binding in view.bindings]
            view.section.set_counts(
                own=sum(state.own for state in states),
                code=sum(state.code is not None for state in states),
                errors=sum(state.error is not None for state in states),
                warnings=sum(state.warning is not None for state in states),
            )
            if view.pick is not None and self._picker is not None:
                view.pick.setEnabled(self._picker.unavailable is None)
                view.pick.setToolTip(self._picker.unavailable or "")
            if view.advanced is not None:  # shown with its settings, e.g. when feature matching is on
                view.advanced.setVisible(any(not b.field.isHidden() for b in view.bindings if b.descriptor.advanced))


def _pick_position(store: Store, picker: ScreenPicker) -> None:
    """Sets both axes of the fixed position, absolute, to a point picked on screen, as one undo step."""
    screen = resolve("screen", store.document, store.default, include_code=store.include_code).value

    def picked(x: int, y: int) -> None:
        store.set_fields(ELEMENT, {"x": x, "rel_x": None, "y": y, "rel_y": None}, PICK)

    picker.pick_point(screen, picked)
