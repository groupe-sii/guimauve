"""Dynamic properties read by the stylesheet."""

from typing import Any

from PySide6.QtWidgets import QWidget


def set_style_property(widget: QWidget, name: str, value: Any) -> None:
    """Changes a property read by the stylesheet and applies it, to the widget and to its children.

    Qt only reads dynamic properties when a widget is polished, so a change needs a new polish; children are
    polished too, for rules that select them through their parent.
    """
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    for target in (widget, *widget.findChildren(QWidget)):
        target.style().unpolish(target)
        target.style().polish(target)
