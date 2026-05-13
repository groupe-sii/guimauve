from typing import Optional

import numpy as np
from sugar import Schema

from guimauve.models.area import Area
from guimauve.models.params import ImageParams, LocateParams, MatchParams, MouseParams, TextParams


class Variant(LocateParams, MouseParams, MatchParams):
    name: str


class Target(Schema):
    name: str
    x: int
    y: int


class ImageVariant(Variant, ImageParams):
    path: str
    image: Optional[np.ndarray]
    targets: Optional[list[Target]]
    default_target: Optional[str]
    match_area: Optional[Area]


class TextVariant(Variant, TextParams):
    text: str
