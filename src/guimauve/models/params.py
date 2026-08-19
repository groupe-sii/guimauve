from typing import Annotated, Optional, Union

from guimauve.enums import MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.base import Bounds, Model


class LocateParams(Model):
    search_area: Optional[Union[Area, ScreenArea]] = None


class MouseParams(Model):
    mouse_direction: Optional[MouseDirection] = None
    # 0 is a meaningful value here (instant move, no animation), not invalid — only negative is.
    mouse_speed: Annotated[Optional[Union[int, float]], Bounds(min=0)] = None


class ImageParams(Model):
    use_template: Optional[bool] = None
    template_grayscale: Optional[bool] = None
    template_confidence_threshold: Annotated[Optional[Union[int, float]], Bounds(min=0.0, max=1.0)] = None

    use_feature: Optional[bool] = None
    feature_n_features: Annotated[Optional[int], Bounds(min=10, max=5000)] = None
    feature_contrast_threshold: Annotated[Optional[float], Bounds(min=0.01, max=0.2)] = None
    feature_edge_threshold: Annotated[Optional[int], Bounds(min=1, max=50)] = None
    feature_sigma: Annotated[Optional[float], Bounds(min=0.5, max=3.0)] = None
    feature_lowe_ratio: Annotated[Optional[float], Bounds(min=0.4, max=0.95)] = None
    feature_min_points: Annotated[Optional[int], Bounds(min=4, max=50)] = None
    feature_ransac_threshold: Annotated[Optional[float], Bounds(min=1.0, max=5.0)] = None
    feature_ratio_tolerance: Annotated[Optional[float], Bounds(min=0.01, max=2.0)] = None
    feature_size_tolerance: Annotated[Optional[float], Bounds(min=0.1, max=8.0)] = None

    use_ocr: Optional[bool] = None
    ocr_confidence_threshold: Annotated[Optional[float], Bounds(min=0.0, max=1.0)] = None
    ocr_fidelity: Optional[OcrFidelity] = None


class TextParams(Model):
    text_confidence_threshold: Annotated[Optional[Union[int, float]], Bounds(min=0.0, max=1.0)] = None
    text_fidelity: Optional[OcrFidelity] = None


class MatchParams(Model):
    match_index: Annotated[Optional[int], Bounds(min=0, max=1000)] = None
    match_sort: Optional[MatchSort] = None


class ElementParams(Model):
    timeout: Annotated[Optional[Union[int, float]], Bounds(min=0)] = None
    target: Optional[Union[str, list[int]]] = None
    find_all: Optional[bool] = None
