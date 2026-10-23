"""Editing tools of the canvas."""

from enum import Enum


class Tool(Enum):
    SELECT = "select"
    TARGET = "target"
    MATCH_AREA = "match_area"
    CROP = "crop"


HELP = {
    Tool.TARGET: "Click to add a target. Esc to finish.",
}
"""Help shown in the bar above the canvas while a tool is active."""
