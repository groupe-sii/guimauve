from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from guimauve.enums import MatchSort

if TYPE_CHECKING:  # detector imports this module
    from guimauve.detection.detector import Match

# Direction of each axis for a corner: 1 when the corner is on the low side of the axis (left, top), -1 otherwise.
_CORNERS: dict[MatchSort, tuple[int, int]] = {
    MatchSort.TOP_LEFT: (1, 1),
    MatchSort.TOP_RIGHT: (-1, 1),
    MatchSort.BOTTOM_LEFT: (1, -1),
    MatchSort.BOTTOM_RIGHT: (-1, -1),
}


def position_key(match: Match, corner: MatchSort) -> tuple[int, int, int]:
    """Sort key of a match by its distance to a corner, the nearest first.

    The distance is measured along the diagonal (x + y, with each axis flipped for the corners on its high side). On a
    tie, the match nearest the corner horizontally comes first, then vertically, so that the order never depends on
    the order of detection.

    :param match: Match to sort; only its target is used.
    :param corner: One of the corner values of ``MatchSort``.
    :return: The sort key.
    """
    sx, sy = _CORNERS[corner]
    x, y = sx * match.target.x, sy * match.target.y
    return x + y, x, y


def sort_matches(matches: Iterable[Match], match_sort: MatchSort | None) -> list[Match]:
    """Sorts matches found on one image.

    :param matches: Matches to sort.
    :param match_sort: Order to sort them in; None keeps their order.
    :return: The sorted matches, as a new list.
    """
    return [match for _, match in sort_ranked(((0, match) for match in matches), match_sort)]


def sort_ranked(ranked: Iterable[tuple[int, Match]], match_sort: MatchSort | None) -> list[tuple[int, Match]]:
    """Sorts matches grouped by rank, e.g. the rank of their screen in the list of screens searched.

    Matches of a lower rank always come first; matches of the same rank are sorted by ``match_sort``. The sort is
    stable: matches with the same key keep their order.

    :param ranked: Pairs of (rank, match).
    :param match_sort: Order to sort the matches of a same rank in; None keeps their order.
    :return: The sorted pairs, as a new list.
    """
    if match_sort is MatchSort.CONFIDENCE:
        return sorted(ranked, key=lambda pair: (pair[0], -pair[1].confidence))
    if match_sort in _CORNERS:
        return sorted(ranked, key=lambda pair: (pair[0], *position_key(pair[1], match_sort)))
    return sorted(ranked, key=lambda pair: pair[0])
