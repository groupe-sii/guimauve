"""Inspector: the properties of the element, by section, generated from the schema."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import Disclosure, PropertyField, Section
from guimauve.gui.element_editor_next.panels.field_binding import FieldBinding
from guimauve.gui.element_editor_next.schema import FIELDS, SECTIONS, SectionDescriptor
from guimauve.gui.element_editor_next.state import ELEMENT, Store, resolve
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

ADVANCED = "Advanced"
NOTES = {"fixed_position": "An axis not set keeps the mouse position."}


class _SectionView:
    """A section of the inspector with its fields, and its advanced group if any."""

    def __init__(self, store: Store, descriptor: SectionDescriptor, theme: ThemeManager):
        self.descriptor = descriptor
        self.section = Section(descriptor.title, theme)
        self.bindings = [FieldBinding(store, field, theme) for field in descriptor.fields]
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
        self.section.set_content(body)


class Inspector(QScrollArea):
    """Element tab: every property by section, bound to the store.

    Sections are collapsed when they appear, with badges counting the values set here, the code values and the
    issues. A detection section is hidden until the element has a variant of its kind.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._store = store
        self._views = [_SectionView(store, descriptor, theme) for descriptor in SECTIONS]
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
            if view.advanced is not None:  # shown with its settings, e.g. when feature matching is on
                view.advanced.setVisible(any(not b.field.isHidden() for b in view.bindings if b.descriptor.advanced))

    def reveal(self, owner: int | None, field: str | None) -> bool:
        """Opens the section of a field, scrolls to it and gives it the focus, e.g. from the issues pill.

        :return: False when the field is not shown in this tab, e.g. hidden or of another owner.
        """
        if owner is not ELEMENT or field not in FIELDS:
            return False
        descriptor = FIELDS[field]
        for view in self._views:
            binding = next((b for b in view.bindings if b.descriptor is descriptor), None)
            if binding is None:
                continue
            if view.section.isHidden() or binding.field.isHidden():
                return False
            view.section.set_open(True)
            if descriptor.advanced and view.advanced is not None:
                view.advanced.set_open(True)
            # Once the layout has placed the opened section.
            QTimer.singleShot(0, self, lambda: self._focus(binding.field))  # dropped if the inspector goes
            return True
        return False

    def _focus(self, field: PropertyField) -> None:
        self.ensureWidgetVisible(field)
        for widget in [field.editor, *field.editor.findChildren(QWidget)]:
            if widget.isVisible() and widget.isEnabled() and widget.focusPolicy() & Qt.FocusPolicy.TabFocus:
                widget.setFocus()
                return
