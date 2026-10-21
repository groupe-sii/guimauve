"""One property field bound to the store, for the element or a variant."""

from collections.abc import Callable

from guimauve.gui.element_editor_next.components import (
    AxisEditor,
    AxisPosition,
    FieldEditor,
    FieldState,
    PropertyField,
    ScreenEditor,
    SearchAreaEditor,
    TargetEditor,
    axis_resolution,
    axis_values,
    editor_for,
    field_state,
)
from guimauve.gui.element_editor_next.schema import FieldDescriptor, Values
from guimauve.gui.element_editor_next.state import ELEMENT, Resolution, Store, resolve
from guimauve.gui.element_editor_next.theme import ThemeManager
from guimauve.models.variant import ImageVariant

NO_EFFECT = "No effect with a fixed position"
ONE_SCREEN = "Only one screen with VNC"

_SPECIAL: dict[str, Callable[[ThemeManager], FieldEditor]] = {
    "target": lambda theme: TargetEditor(),
    "search_area": lambda theme: SearchAreaEditor(),
    "screen": ScreenEditor,
}


def make_editor(descriptor: FieldDescriptor, theme: ThemeManager) -> FieldEditor:
    """Editor of a field: an axis, a special field, or the generic editor of its type."""
    if descriptor.relative is not None:
        return AxisEditor(descriptor)
    if descriptor.key in _SPECIAL:
        return _SPECIAL[descriptor.key](theme)
    editor = editor_for(descriptor, theme)
    assert editor is not None, f"no editor for {descriptor.key}"
    return editor


class FieldBinding:
    """Sends the edits of a field to the store and shows its state from the store.

    A continuous edit, such as dragging a slider, is one undo step: a gesture runs from edit_started to
    edit_finished. An axis of the fixed position sets its two fields as one step.

    :param owner: ELEMENT, or the key of a variant.
    """

    def __init__(self, store: Store, descriptor: FieldDescriptor, theme: ThemeManager, owner: int | None = ELEMENT):
        self._store, self.descriptor, self._owner = store, descriptor, owner
        self._gesture: int | None = None
        self.field = PropertyField(descriptor, make_editor(descriptor, theme), theme)
        self.field.edited.connect(self._edit)
        self.field.reset_requested.connect(lambda: self._edit(None))
        self.field.edit_started.connect(self._start_gesture)
        self.field.edit_finished.connect(self._finish_gesture)

    def refresh(self, values: Values) -> FieldState:
        """Shows the state of the field; values are the resolved ones of the owner, for the display rules."""
        store, descriptor = self._store, self.descriptor
        editor = self.field.editor
        reason = None
        if not descriptor.effective(values):
            reason = NO_EFFECT
        elif isinstance(editor, ScreenEditor) and not store.screens:
            reason = ONE_SCREEN

        if isinstance(editor, TargetEditor):
            editor.set_names(shared_target_names(store))
        elif isinstance(editor, ScreenEditor):
            editor.set_screens(store.screens)
        elif isinstance(editor, AxisEditor):
            editor.set_negative_allowed(values.get("screen") == 0)

        issues = [issue for key in descriptor.keys for issue in store.issues_of(self._owner, key)]
        state = field_state(self._resolution(), self._owner is not ELEMENT, issues, reason)
        self.field.set_state(state)
        self.field.setVisible(descriptor.visible(values))
        return state

    def _resolution(self) -> Resolution:
        store = self._store
        variant = None if self._owner is ELEMENT else store.document.get(self._owner)
        resolutions = [
            resolve(key, store.document, store.default, variant, include_code=store.include_code)
            for key in self.descriptor.keys
        ]
        return resolutions[0] if len(resolutions) == 1 else axis_resolution(*resolutions)

    def _edit(self, value: object) -> None:
        descriptor, store = self.descriptor, self._store
        if descriptor.relative is None:
            store.set_field(self._owner, descriptor.key, value, descriptor.label, self._gesture)
            return
        assert value is None or isinstance(value, AxisPosition)
        absolute, relative = axis_values(value)
        store.set_fields(self._owner, {descriptor.key: absolute, descriptor.relative: relative}, descriptor.label)

    def _start_gesture(self) -> None:
        self._gesture = self._store.new_gesture()

    def _finish_gesture(self) -> None:
        self._gesture = None


def shared_target_names(store: Store) -> list[str]:
    """Names of the targets defined in every image variant, in the order of the first one."""
    images = [variant for variant in store.document.variants if isinstance(variant, ImageVariant)]
    if not images:
        return []
    names = [target.name for target in images[0].targets or [] if target.name]
    return [name for name in names if all(any(t.name == name for t in v.targets or []) for v in images[1:])]
