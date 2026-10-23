"""Editing tools of the canvas."""

from enum import Enum


class Tool(Enum):
    SELECT = "select"
    TARGET = "target"
    MATCH_AREA = "match_area"
    CROP = "crop"


REGION_TOOLS = (Tool.MATCH_AREA, Tool.CROP)
"""Tools editing a rectangle on the image."""
HELP = {
    Tool.TARGET: "Click to add a target. Esc to finish.",
    Tool.MATCH_AREA: "Drag the handles. Enter to apply, Esc to cancel.",
}
"""Help shown in the bar above the canvas while a tool is active."""
