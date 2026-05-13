from typing import Literal, Optional, Union

from sugar import Schema

from guimauve.enums import Key, MatchSort, MouseDirection, ScreenArea
from guimauve.models.parameters.screenshot import Screenshot
from guimauve.models.parameters.vnc import VNC
from guimauve.models.params import ElementParams, ImageParams, LocateParams, MatchParams, MouseParams, TextParams


class DefaultParams(ElementParams, LocateParams, MouseParams, ImageParams, TextParams, MatchParams):
    search_area = ScreenArea.FULL

    mouse_direction = MouseDirection.STRAIGHT

    use_template = True
    template_grayscale = True
    template_confidence_threshold = 0.95

    use_feature = False
    feature_n_features = 2000
    feature_contrast_threshold = 0.04
    feature_edge_threshold = 10
    feature_sigma = 1.6
    feature_lowe_ratio = 0.8
    feature_min_points = 6
    feature_ransac_threshold = 5.0
    feature_ratio_tolerance = 0.1
    feature_size_tolerance = 0.2

    use_ocr = False
    ocr_confidence_threshold = 0.8

    text_threshold = 0.75
    text_language = "en"
    text_case_sensitive = False

    match_index = 0
    match_sort = MatchSort.XY_POSITION

    timeout = 5
    find_all = False


class Parameters(Schema):
    execution_mode: Literal["local", "vnc"] = "local"
    vnc: Optional[VNC]
    debug_elements: bool = False
    debug_replays: bool = False
    sleep: Union[int, float] = 0
    pause_shortcut: list[Key] = [Key.CTRL, Key.SHIFT, Key.ALT]
    screenshot: Screenshot = Screenshot()
    default: DefaultParams = DefaultParams()

    def validate_sleep(self):
        if self.sleep < 0:
            yield "must be a positive number"
