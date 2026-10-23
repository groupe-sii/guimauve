import numpy as np
import pytest

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state import ELEMENT, Document, Severity, can_save, validate
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant

SCREENS = [Screen(0, 0, 3840, 1080), Screen(0, 0, 1920, 1080), Screen(1920, 0, 1920, 1080)]


def image(width=20, height=10):
    return np.zeros((height, width, 3), dtype=np.uint8)


@pytest.fixture
def document():
    return Document(
        Element(
            name="button",
            variants=[
                ImageVariant(name="light", image=image(), targets=[Target(name="icon", x=1, y=2)]),
                TextVariant(name="label", text="OK"),
            ],
        )
    )


def codes(issues):
    return [issue.code for issue in issues]


def test_valid_document(document):
    issues = validate(document)

    assert issues == []
    assert can_save(issues)


def test_image_in_memory_without_file_is_valid(document):
    assert document.variants[0].path is None
    assert validate(document) == []


def test_missing_image(document):
    document.variants[0].image = None

    (issue,) = validate(document)

    assert (issue.code, issue.owner, issue.field) == ("image_missing", document.key(document.variants[0]), "image")
    assert not can_save([issue])


def test_element_field_error(document):
    document.element.mouse_speed = -1

    (issue,) = validate(document)

    assert (issue.owner, issue.field, issue.severity) == (ELEMENT, "mouse_speed", Severity.ERROR)


def test_variant_field_error(document):
    variant = document.variants[1]
    variant.text = ""

    (issue,) = validate(document)

    assert (issue.owner, issue.field, issue.code) == (document.key(variant), "text", "empty")


def test_target_field_error(document):
    target = document.variants[0].targets[0]
    target.name = " "

    (issue,) = validate(document)

    assert (issue.owner, issue.field) == (document.key(target), "name")


def test_target_not_found_goes_on_each_variant(document):
    other = ImageVariant(name="dark", image=image(), targets=[Target(name="icon", x=1, y=1)])
    document.element.variants.append(other)
    document.element.target = "close"

    issues = validate(document)

    assert codes(issues) == ["target_not_found", "target_not_found"]
    assert [issue.owner for issue in issues] == [document.key(document.variants[0]), document.key(other)]


def test_duplicate_names_go_on_each_variant(document):
    document.variants[1].name = "light"

    issues = validate(document)

    assert [(issue.owner, issue.field) for issue in issues] == [
        (document.key(document.variants[0]), "name"),
        (document.key(document.variants[1]), "name"),
    ]


def test_element_checks_run_despite_field_errors(document):
    document.element.mouse_speed = -1
    document.variants[1].name = "light"

    assert sorted(codes(validate(document))) == [
        "duplicate_variant_name",
        "duplicate_variant_name",
        "greater_than_equal",
    ]


def test_coordinate_conflict_goes_on_axis(document):
    document.element.y = 1
    document.element.rel_y = 2

    (issue,) = validate(document)

    assert (issue.owner, issue.field) == (ELEMENT, "y")


def test_no_variant_and_no_position(document):
    document.element.variants = None

    assert codes(validate(document)) == ["no_locator"]


@pytest.mark.parametrize(("x", "y"), [(20, 0), (0, 10), (-1, 0)])
def test_target_outside_image_is_a_warning(document, x, y):
    target = document.variants[0].targets[0]
    target.x, target.y = x, y

    issues = validate(document)

    assert [(issue.owner, issue.severity) for issue in issues] == [(document.key(target), Severity.WARNING)]
    assert can_save(issues)


@pytest.mark.parametrize(("screen", "missing"), [(3, [3]), ([2, 4, 5], [4, 5]), (0, []), (2, [])])
def test_screen_not_connected_is_a_warning(document, screen, missing):
    document.element.screen = screen

    issues = validate(document, SCREENS)

    assert [issue.message for issue in issues] == [f"Screen {n} is not connected" for n in missing]
    assert all(issue.severity is Severity.WARNING and issue.field == "screen" for issue in issues)


def test_screens_unknown(document):
    document.element.screen = 5

    assert validate(document, []) == []


def test_validation_does_not_modify_document(document):
    document.element.mouse_speed = -1

    validate(document)

    assert document.element.mouse_speed == -1
    assert document.is_modified()


@pytest.mark.parametrize("axis", ["x", "y"])
def test_negative_position_goes_on_axis(document, axis):
    setattr(document.element, axis, -10)

    (issue,) = validate(document)

    assert (issue.code, issue.owner, issue.field) == ("position_negative", ELEMENT, axis)


def test_negative_position_is_valid_from_the_primary_screen(document):
    document.element.screen = 0
    document.element.x = -10

    assert validate(document, SCREENS) == []


@pytest.mark.parametrize(
    ("screen", "x", "y", "fields"),
    [(None, 1920, 0, ["x"]), (2, 0, 1080, ["y"]), ([2, 1], 1919, 1079, []), (0, 5000, 5000, [])],
)
def test_position_beyond_its_screen_is_a_warning(document, screen, x, y, fields):
    document.element.screen, document.element.x, document.element.y = screen, x, y

    issues = validate(document, SCREENS)

    assert [issue.field for issue in issues] == fields
    assert all(issue.code == "position_outside_screen" and issue.severity is Severity.WARNING for issue in issues)


def test_single_unnamed_target_is_valid():
    variant = ImageVariant(name="light", image=image(), targets=[Target(x=1, y=2)])

    assert "target_unnamed" not in codes(validate(Document(Element(name="button", variants=[variant]))))


def test_unnamed_target_among_several_is_a_warning():
    variant = ImageVariant(name="light", image=image(), targets=[Target(name="icon", x=1, y=2), Target(x=3, y=4)])
    document = Document(Element(name="button", variants=[variant]))

    issues = [issue for issue in validate(document) if issue.code == "target_unnamed"]

    assert [(issue.severity, issue.owner, issue.field) for issue in issues] == [
        (Severity.WARNING, document.key(document.variants[0].targets[1]), "name")
    ]
    assert can_save(validate(document))
