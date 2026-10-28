"""Outcome of a search of the Test mode, as the store keeps it."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from guimauve.detection.detector import Match
from guimauve.models.element import Element

if TYPE_CHECKING:  # the detection loads the OCR models, too slow to import with the state
    from guimauve.detection.locate import LocateReport


class TestScope(Enum):
    """What a test searches."""

    __test__ = False  # not a test class for pytest

    VARIANT = "variant"
    """The selected variant alone."""
    ELEMENT = "element"
    """Every variant, in order, as a run does."""


@dataclass(frozen=True)
class TestResult:
    """Outcome of one search of the Test mode.

    :param scope: What was searched.
    :param variant: Key of the variant searched; None for the element.
    :param report: Outcome of the search; None when it failed, see error.
    :param captures: Captures searched, by screen number.
    :param include_code: Whether the code overrides applied.
    :param duration: Seconds the search took.
    :param used: Index in report.matches of the match a run would use, by match_index; None when there is none.
    :param error: Why the search failed, or why no match is used although some were found.
    :param element: Element searched, resolved; None when unknown.
    """

    __test__ = False  # not a test class for pytest

    scope: TestScope
    variant: int | None
    report: "LocateReport | None"
    captures: dict[int, np.ndarray] = field(default_factory=dict)
    include_code: bool = True
    duration: float = 0.0
    used: int | None = None
    error: str | None = None
    element: Element | None = None

    @property
    def used_match(self) -> Match | None:
        """The match a run would use, if any."""
        if self.report is None or self.used is None:
            return None
        return self.report.matches[self.used]
