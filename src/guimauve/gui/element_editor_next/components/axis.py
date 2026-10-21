"""One axis of a fixed position, edited as one value from two fields; without Qt."""

from dataclasses import dataclass
from enum import Enum

from guimauve.gui.element_editor_next.state import Resolution, Source


class AxisMode(Enum):
    NOT_SET = "not_set"
    ABSOLUTE = "absolute"
    FROM_MOUSE = "from_mouse"


@dataclass(frozen=True)
class AxisPosition:
    """Position on one axis: on the screen (x), from the mouse (rel_x), or not set to keep the mouse position.

    :param amount: Pixels from the left or top of the screen, or from the mouse; 0 when not set.
    """

    mode: AxisMode
    amount: int = 0

    @property
    def label(self) -> str:
        """Short text, e.g. "1280", "mouse + 10" or "mouse − 10"."""
        if self.mode is AxisMode.ABSOLUTE:
            return str(self.amount)
        if self.mode is AxisMode.FROM_MOUSE:
            return f"mouse {'−' if self.amount < 0 else '+'} {abs(self.amount)}"
        return "not set"


NOT_SET = AxisPosition(AxisMode.NOT_SET)


def axis_position(absolute: int | None, relative: int | None) -> AxisPosition:
    """Position from the two fields of the axis; the absolute one wins, as when the element is located."""
    if absolute is not None:
        return AxisPosition(AxisMode.ABSOLUTE, absolute)
    if relative is not None:
        return AxisPosition(AxisMode.FROM_MOUSE, relative)
    return NOT_SET


def axis_values(position: AxisPosition | None) -> tuple[int | None, int | None]:
    """Absolute and relative fields for a position: at most one of them is set."""
    if position is None or position.mode is AxisMode.NOT_SET:
        return None, None
    if position.mode is AxisMode.ABSOLUTE:
        return position.amount, None
    return None, position.amount


def axis_resolution(absolute: Resolution, relative: Resolution) -> Resolution:
    """Merges the resolutions of the two fields: each layer defining one of them gives a position."""
    sources = [source for source in Source if source in absolute.layers or source in relative.layers]
    layers = {source: axis_position(absolute.layers.get(source), relative.layers.get(source)) for source in sources}
    if not layers:
        return Resolution(None, None, {})
    return Resolution(layers[sources[-1]], sources[-1], layers)
