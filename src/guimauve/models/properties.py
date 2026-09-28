from pydantic import Field

from guimauve.enums import MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.model import Model


class LocateProperties(Model):
    search_area: Area | ScreenArea | None = None


class MouseProperties(Model):
    mouse_direction: MouseDirection | None = None
    mouse_speed: int | None = Field(default=None, ge=0, le=5000)


class ImageProperties(Model):
    use_template: bool | None = None
    template_grayscale: bool | None = None
    template_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)

    use_feature: bool | None = None
    feature_n_features: int | None = Field(default=None, ge=10, le=5000)
    feature_contrast_threshold: float | None = Field(default=None, ge=0.01, le=0.2)
    feature_edge_threshold: int | None = Field(default=None, ge=1, le=50)
    feature_sigma: float | None = Field(default=None, ge=0.5, le=3.0)
    feature_lowe_ratio: float | None = Field(default=None, ge=0.4, le=0.95)
    feature_min_points: int | None = Field(default=None, ge=4, le=50)
    feature_ransac_threshold: float | None = Field(default=None, ge=1.0, le=5.0)
    feature_ratio_tolerance: float | None = Field(default=None, ge=0.01, le=2.0)
    feature_size_tolerance: float | None = Field(default=None, ge=0.1, le=8.0)

    use_ocr: bool | None = None
    ocr_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    ocr_fidelity: OcrFidelity | None = None


class TextProperties(Model):
    text_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    text_fidelity: OcrFidelity | None = None


class MatchProperties(Model):
    match_index: int | None = Field(default=None, ge=0, le=1000)
    match_sort: MatchSort | None = None


class ElementProperties(Model):
    timeout: int | float | None = Field(default=None, ge=0)
    target: str | list[int] | None = None
    find_all: bool | None = None
