import pytest

from guimauve.detection.detector import Match, Point
from guimauve.detection.sort import sort_matches, sort_ranked
from guimauve.enums import MatchSort


def match(x, y, confidence=1.0) -> Match:
    return Match(box=None, target=Point(x, y), confidence=confidence)


def targets(matches) -> list[tuple[int, int]]:
    return [tuple(m.target) for m in matches]


# Four matches, one near each corner of a 1000x1000 image.
CORNERS = [match(900, 900), match(100, 900), match(900, 100), match(100, 100)]


@pytest.mark.parametrize(
    ("corner", "first"),
    [
        (MatchSort.TOP_LEFT, (100, 100)),
        (MatchSort.TOP_RIGHT, (900, 100)),
        (MatchSort.BOTTOM_LEFT, (100, 900)),
        (MatchSort.BOTTOM_RIGHT, (900, 900)),
    ],
)
def test_each_corner_puts_the_nearest_match_first(corner, first):
    assert targets(sort_matches(CORNERS, corner))[0] == first


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        # (0, 100) and (100, 0) are equally far from the top-left and bottom-right corners along the diagonal
        (MatchSort.TOP_LEFT, [(0, 100), (100, 0)]),
        (MatchSort.BOTTOM_RIGHT, [(100, 0), (0, 100)]),
        # (0, 0) and (100, 100) are equally far from the top-right and bottom-left corners
        (MatchSort.TOP_RIGHT, [(100, 100), (0, 0)]),
        (MatchSort.BOTTOM_LEFT, [(0, 0), (100, 100)]),
    ],
)
def test_tie_is_broken_by_the_match_nearest_the_corner_horizontally(corner, expected):
    tied = [match(*point) for point in expected]
    assert targets(sort_matches(tied, corner)) == expected
    assert targets(sort_matches(list(reversed(tied)), corner)) == expected


@pytest.mark.parametrize(
    "corner", [MatchSort.TOP_LEFT, MatchSort.TOP_RIGHT, MatchSort.BOTTOM_LEFT, MatchSort.BOTTOM_RIGHT]
)
def test_order_does_not_depend_on_the_order_of_detection(corner):
    matches = [match(30, 70), match(70, 30), match(50, 50), match(0, 100), match(100, 0)]
    assert targets(sort_matches(matches, corner)) == targets(sort_matches(list(reversed(matches)), corner))


def test_negative_coordinates_are_sorted_like_any_others():
    # screens left of or above the primary one have negative desktop coordinates
    matches = [match(10, 10), match(-1270, 20), match(-500, -300)]
    assert targets(sort_matches(matches, MatchSort.TOP_LEFT)) == [(-1270, 20), (-500, -300), (10, 10)]
    assert targets(sort_matches(matches, MatchSort.BOTTOM_RIGHT)) == [(10, 10), (-500, -300), (-1270, 20)]


def test_confidence_puts_the_best_score_first():
    matches = [match(1, 1, 0.7), match(2, 2, 0.9), match(3, 3, 0.8)]
    assert [m.confidence for m in sort_matches(matches, MatchSort.CONFIDENCE)] == [0.9, 0.8, 0.7]


def test_no_sort_keeps_the_order():
    assert sort_matches(CORNERS, None) == CORNERS


def test_sort_returns_a_new_list():
    matches = list(CORNERS)
    sort_matches(matches, MatchSort.TOP_LEFT)
    assert matches == CORNERS


def test_xy_position_is_the_former_name_of_top_left():
    assert MatchSort.XY_POSITION is MatchSort.TOP_LEFT
    assert MatchSort["XY_POSITION"] is MatchSort.TOP_LEFT
    # listed once, e.g. in the editor
    assert [sort.name for sort in MatchSort] == ["CONFIDENCE", "TOP_LEFT", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_RIGHT"]


# --- by rank ---


@pytest.mark.parametrize("match_sort", [MatchSort.TOP_LEFT, MatchSort.BOTTOM_RIGHT, MatchSort.CONFIDENCE, None])
def test_lower_rank_always_comes_first(match_sort):
    ranked = [(1, match(0, 0, 1.0)), (0, match(900, 900, 0.1)), (1, match(5, 5, 0.5)), (0, match(10, 10, 0.2))]
    assert [rank for rank, _ in sort_ranked(ranked, match_sort)] == [0, 0, 1, 1]


def test_matches_of_a_same_rank_are_sorted_by_position():
    ranked = [(1, match(500, 500)), (0, match(900, 900)), (1, match(5, 5)), (0, match(10, 10))]
    assert [(rank, tuple(m.target)) for rank, m in sort_ranked(ranked, MatchSort.TOP_LEFT)] == [
        (0, (10, 10)),
        (0, (900, 900)),
        (1, (5, 5)),
        (1, (500, 500)),
    ]


def test_former_name_in_a_dataset_loads_as_top_left_and_is_saved_under_the_new_name():
    from guimauve.models.element import Element

    element = Element(name="E", match_sort="XY_POSITION", x=1, y=1)
    assert element.resolve() == []
    assert element.match_sort is MatchSort.TOP_LEFT
    assert "match_sort: TOP_LEFT" in element.to_yaml()
