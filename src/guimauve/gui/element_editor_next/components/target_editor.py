"""Editor of the target of the element: which target of the variants is clicked."""

from typing import Any

from guimauve.gui.element_editor_next.components.editors import SEPARATOR, ComboEditor, Option

DEFAULT_HINT = "Default target of each variant, else the centre of the match"


class TargetEditor(ComboEditor):
    """Default, then the target names shared by the image variants.

    A name missing from the variants keeps its entry: the validation reports it on the variants. A point [x, y]
    is shown but never created here, since a target is placed on the canvas.
    """

    _names: tuple[str, ...] = ()

    def set_names(self, names: list[str]) -> None:
        """Target names defined in every image variant, in display order."""
        if tuple(names) != self._names:
            self._names = tuple(names)
            self.refresh()

    def options(self, value: Any) -> list[Option | object]:
        options: list[Option | object] = [Option(None, "Default", DEFAULT_HINT)]
        names = [*self._names, *([value] if isinstance(value, str) and value not in self._names else [])]
        if names:
            options += [SEPARATOR, *(Option(name, name) for name in names)]
        if isinstance(value, list | tuple):
            x, y = value
            options += [SEPARATOR, Option(value, f"Point x {x}, y {y}", "Same point in the image of every variant")]
        return options
