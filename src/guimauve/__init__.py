import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from guimauve.controller import Controller
    from guimauve.enums import Button, Key, MatchSort, Menu, MouseDirection, OcrFidelity, ScreenArea
    from guimauve.models.area import Area
    from guimauve.models.data import Data
    from guimauve.models.element import Element
    from guimauve.models.parameters.parameters import Parameters
    from guimauve.models.parameters.vnc import VNC
    from guimauve.models.replay import Replay
    from guimauve.models.variant import ImageVariant, TextVariant

__all__ = [
    "Controller",
    "Button",
    "Key",
    "MatchSort",
    "Menu",
    "MouseDirection",
    "OcrFidelity",
    "ScreenArea",
    "Area",
    "Data",
    "Element",
    "Parameters",
    "VNC",
    "Replay",
    "ImageVariant",
    "TextVariant",
]

_MAPPING = {
    "Controller": "guimauve.controller",
    "Button": "guimauve.enums",
    "Key": "guimauve.enums",
    "MatchSort": "guimauve.enums",
    "Menu": "guimauve.enums",
    "MouseDirection": "guimauve.enums",
    "OcrFidelity": "guimauve.enums",
    "ScreenArea": "guimauve.enums",
    "Area": "guimauve.models.area",
    "Data": "guimauve.models.data",
    "Element": "guimauve.models.element",
    "Parameters": "guimauve.models.parameters.parameters",
    "VNC": "guimauve.models.parameters.vnc",
    "Replay": "guimauve.models.replay",
    "ImageVariant": "guimauve.models.variant",
    "TextVariant": "guimauve.models.variant",
}


def __getattr__(name: str) -> Any:
    if name in _MAPPING:
        module_path = _MAPPING[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)

        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__():
    return sorted(__all__)
