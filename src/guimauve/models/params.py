from typing import Optional, Union

from sugar import Schema

from guimauve.enums import MatchSort, MouseDirection, ScreenArea
from guimauve.models.area import Area


class LocateParams(Schema):
    search_area: Optional[Union[Area, ScreenArea]]


class MouseParams(Schema):
    mouse_direction: Optional[MouseDirection]
    mouse_speed: Optional[Union[int, float]]


class ImageParams(Schema):
    use_template: Optional[bool]
    template_grayscale: Optional[bool]
    template_confidence_threshold: Optional[Union[int, float]]

    use_feature: Optional[bool]
    feature_n_features: Optional[int]
    feature_contrast_threshold: Optional[float]
    feature_edge_threshold: Optional[int]
    feature_sigma: Optional[float]
    feature_lowe_ratio: Optional[float]
    feature_min_points: Optional[int]
    feature_ransac_threshold: Optional[float]
    feature_ratio_tolerance: Optional[float]
    feature_size_tolerance: Optional[float]

    use_ocr: Optional[bool]
    ocr_confidence_threshold: Optional[float]


class TextParams(Schema):
    text_threshold: Optional[Union[int, float]]
    text_language: Optional[str]
    text_case_sensitive: Optional[bool]


class MatchParams(Schema):
    match_index: Optional[int]
    match_sort: Optional[MatchSort]


class ElementParams(Schema):
    timeout: Optional[Union[int, float]]
    target: Optional[Union[str, list[int]]]
    find_all: Optional[bool]
