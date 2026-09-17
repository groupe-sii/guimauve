from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, NonNegativeFloat, NonNegativeInt, field_validator, model_validator
from pydantic_core import PydanticCustomError

from guimauve.enums import Key, MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.model import Model, check_all
from guimauve.models.properties import (
    ElementProperties,
    ImageProperties,
    LocateProperties,
    MatchProperties,
    MouseProperties,
    TextProperties,
)

# Real defaults for DefaultProperties, applied via a before-validator: re-annotating a field to
# change its default would silently drop the `Bounds` metadata inherited from the mixins.
_DEFAULT_VALUES = {
    "search_area": ScreenArea.FULL,
    "mouse_direction": MouseDirection.STRAIGHT,
    "use_template": True,
    "template_grayscale": True,
    "template_confidence_threshold": 0.95,
    "use_feature": False,
    "feature_n_features": 2000,
    "feature_contrast_threshold": 0.04,
    "feature_edge_threshold": 10,
    "feature_sigma": 1.6,
    "feature_lowe_ratio": 0.8,
    "feature_min_points": 6,
    "feature_ransac_threshold": 5.0,
    "feature_ratio_tolerance": 0.1,
    "feature_size_tolerance": 0.2,
    "use_ocr": False,
    "ocr_confidence_threshold": 0.8,
    "ocr_fidelity": OcrFidelity.FAST,
    "text_confidence_threshold": 0.8,
    "text_fidelity": OcrFidelity.FAST,
    "match_index": 0,
    "match_sort": MatchSort.XY_POSITION,
    "timeout": 5,
    "find_all": False,
}


class DefaultProperties(
    ElementProperties, LocateProperties, MouseProperties, ImageProperties, TextProperties, MatchProperties
):
    pass


class VNC(Model):
    host: str
    display: Optional[NonNegativeInt] = None
    port: Optional[int] = Field(default=None, gt=0, le=65535)
    password: Optional[str] = None

    @field_validator("host", mode="after")
    @classmethod
    def _host_not_empty(cls, v):
        if not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v

    @model_validator(mode="after")
    def _model_checks(self):
        check_all(self._display_or_port_required)
        return self

    def _display_or_port_required(self):
        if self.display is None and self.port is None:
            raise PydanticCustomError("no_endpoint", "At least a display or a port must be specified")


class ScreenshotActions(Model):
    locate: bool = True
    move: bool = True
    click: bool = True
    scroll: bool = True
    type: bool = True
    press: bool = True


class Screenshot(Model):
    enable: bool = False
    folder: Path = Path("screenshots")
    limit: Optional[int] = Field(default=None, gt=0)
    on: ScreenshotActions = ScreenshotActions()


class Parameters(Model):
    execution_mode: Literal["local", "vnc"] = "local"
    vnc: Optional[VNC] = None
    sleep: NonNegativeFloat = 0.0
    pause_shortcut: list[Key] = [Key.CTRL, Key.SHIFT, Key.ALT]
    screenshot: Screenshot = Screenshot()
    default: DefaultProperties = DefaultProperties(**_DEFAULT_VALUES)
    debug_elements: bool = False
    debug_replays: bool = False
