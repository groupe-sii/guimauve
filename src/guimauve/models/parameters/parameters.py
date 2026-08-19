from typing import Annotated, Literal, Optional, Union

from pydantic import model_validator

from guimauve.enums import Key, MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.base import Bounds, Model
from guimauve.models.parameters.screenshot import Screenshot
from guimauve.models.parameters.vnc import VNC
from guimauve.models.params import ElementParams, ImageParams, LocateParams, MatchParams, MouseParams, TextParams

# Real defaults for DefaultParams, applied via a before-validator: re-annotating a field to
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


class DefaultParams(ElementParams, LocateParams, MouseParams, ImageParams, TextParams, MatchParams):
    @model_validator(mode="before")
    @classmethod
    def _fill_defaults(cls, data):
        if not isinstance(data, dict):
            data = {}
        return {**_DEFAULT_VALUES, **data}


class Parameters(Model):
    execution_mode: Literal["local", "vnc"] = "local"
    vnc: Optional[VNC] = None
    debug_elements: bool = False
    debug_replays: bool = False
    sleep: Annotated[Union[int, float], Bounds(min=0)] = 0
    pause_shortcut: list[Key] = [Key.CTRL, Key.SHIFT, Key.ALT]
    screenshot: Screenshot = Screenshot()
    default: DefaultParams = DefaultParams()
