"""Outcome of a search, apart from the detection so that reading it never loads the OCR."""

from dataclasses import dataclass, field
from enum import Enum, auto

from guimauve.detection.detector import Match
from guimauve.models.variant import Variant


class VariantStatus(Enum):
    FOUND = auto()
    NOT_FOUND = auto()
    SKIPPED = auto()


@dataclass(frozen=True)
class VariantReport:
    """Outcome of the search for one variant."""

    variant: Variant
    status: VariantStatus
    method: str | None = None
    matches: list[Match] = field(default_factory=list)
    unfit_screens: list[int] = field(default_factory=list)  # skipped: the image is larger than their search area
    match_screens: list[int] = field(default_factory=list)  # screen each match was found on, in the same order


@dataclass(frozen=True)
class LocateReport:
    """Outcome of the search for an element."""

    matches: list[Match]
    variants: list[VariantReport] = field(default_factory=list)
    fixed_position: bool = False
    match_screens: list[int] = field(default_factory=list)  # screen each match was found on, in the same order
    match_variants: list[int] = field(default_factory=list)  # index in variants of the variant of each match

    @property
    def found(self) -> bool:
        return bool(self.matches)
