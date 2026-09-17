from typing import Optional, Union

from pydantic import Field

from guimauve.enums import MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.model import Model


class LocateProperties(Model):
    search_area: Optional[Union[Area, ScreenArea]] = None


class MouseProperties(Model):
    mouse_direction: Optional[MouseDirection] = None
    mouse_speed: Optional[int] = Field(default=None, ge=0, le=5000)


class ImageProperties(Model):
    use_template: Optional[bool] = None
    template_grayscale: Optional[bool] = None
    template_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    use_feature: Optional[bool] = None
    feature_n_features: Optional[int] = Field(default=None, ge=10, le=5000)
    feature_contrast_threshold: Optional[float] = Field(default=None, ge=0.01, le=0.2)
    feature_edge_threshold: Optional[int] = Field(default=None, ge=1, le=50)
    feature_sigma: Optional[float] = Field(default=None, ge=0.5, le=3.0)
    feature_lowe_ratio: Optional[float] = Field(default=None, ge=0.4, le=0.95)
    feature_min_points: Optional[int] = Field(default=None, ge=4, le=50)
    feature_ransac_threshold: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    feature_ratio_tolerance: Optional[float] = Field(default=None, ge=0.01, le=2.0)
    feature_size_tolerance: Optional[float] = Field(default=None, ge=0.1, le=8.0)

    use_ocr: Optional[bool] = None
    ocr_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ocr_fidelity: Optional[OcrFidelity] = None


class TextProperties(Model):
    text_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    text_fidelity: Optional[OcrFidelity] = None


class MatchProperties(Model):
    match_index: Optional[int] = Field(default=None, ge=0, le=1000)
    match_sort: Optional[MatchSort] = None


class ElementProperties(Model):
    timeout: Optional[Union[int, float]] = Field(default=None, ge=0)
    target: Optional[Union[str, list[int]]] = None
    find_all: Optional[bool] = None
