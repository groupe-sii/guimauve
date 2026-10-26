"""Problems of the document, attached to the element, a variant, a target or one of their fields."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state.commands import ELEMENT
from guimauve.gui.element_editor_next.state.document import Document
from guimauve.models.variant import ImageVariant

# Image rules replaced by the editor: an image in memory is valid even before its file is written.
_IMAGE_FILE_ERRORS = {"path_missing", "file_not_found"}


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    """A problem of the document.

    :param severity: An error blocks Save and Test; a warning does not.
    :param message: Message shown to the user.
    :param owner: Key of the variant or target, or ELEMENT.
    :param field: Field concerned, or None for the owner as a whole.
    :param code: Error type, from pydantic or from the editor.
    """

    severity: Severity
    message: str
    owner: int | None = ELEMENT
    field: str | None = None
    code: str = ""


def validate(document: Document, screens: list[Screen] | None = None) -> list[Issue]:
    """Lists the problems of the document, without code overrides nor trials.

    :param screens: Screens of the driver, as returned by Driver.screens(); None or empty when unknown.
    """
    issues: list[Issue] = []
    for error in _model_errors(document):
        for issue in _attach(document, error):
            if issue not in issues:
                issues.append(issue)
    issues += _image_issues(document)
    issues += _screen_issues(document, screens or [])
    issues += _position_issues(document, screens or [])
    return issues


def can_save(issues: list[Issue]) -> bool:
    return all(issue.severity is not Severity.ERROR for issue in issues)


def _model_errors(document: Document) -> list[ErrorDetails]:
    errors = document.element.model_copy().resolve()
    # Pydantic skips the element checks when a field is invalid: run them anyway to show every problem at once.
    try:
        document.element._model_checks()  # type: ignore[operator]  # a pydantic model validator
    except ValidationError as e:
        errors += e.errors(include_url=False)
    return [error for error in errors if error["type"] not in _IMAGE_FILE_ERRORS]


def _attach(document: Document, error: ErrorDetails) -> list[Issue]:
    """Attaches a pydantic error to the variant, target or field it concerns."""
    loc, code, message, ctx = error["loc"], error["type"], error["msg"], error.get("ctx") or {}
    variants = document.variants

    if loc and loc[0] == "variants" and len(loc) > 1 and isinstance(loc[1], int):
        variant: Any = variants[loc[1]]
        rest = loc[3:]  # loc[2] is the variant kind
        if len(rest) > 1 and rest[0] == "targets" and isinstance(rest[1], int):
            target = variant.targets[rest[1]]
            return [_error(message, document.key(target), _field(rest[2:]), code)]
        return [_error(message, document.key(variant), _field(rest), code)]

    if code == "target_not_found":
        return [_error(message, document.key(v), "targets", code) for v in variants if v.name in ctx["missing"]]
    if code == "duplicate_variant_name":
        return [_error(message, document.key(v), "name", code) for v in variants if v.name in ctx["duplicates"]]
    if code in ("coordinate_conflict", "position_negative"):
        return [_error(message, ELEMENT, ctx["axis"], code)]
    return [_error(message, ELEMENT, _field(loc), code)]


def _image_issues(document: Document) -> list[Issue]:
    issues = []
    for variant in document.variants:
        if not isinstance(variant, ImageVariant):
            continue
        if variant.image is None:
            issues.append(_error("No image", document.key(variant), "image", "image_missing"))
            continue
        height, width = variant.image.shape[:2]
        targets = variant.targets or []
        for target in targets:
            key = document.key(target)
            if not (0 <= target.x < width and 0 <= target.y < height):
                issues.append(Issue(Severity.WARNING, "Target outside the image", key, None, "target_outside"))
            if target.name is None and len(targets) > 1:  # with several targets, one is chosen by its name
                issues.append(Issue(Severity.WARNING, "Name this target to choose it", key, "name", "target_unnamed"))
    return issues


def _screen_issues(document: Document, screens: list[Screen]) -> list[Issue]:
    screen = document.element.screen
    if not screens or screen is None:
        return []
    connected = range(len(screens))  # 0 bounds all the screens, then 1 to n
    missing = [n for n in (screen if isinstance(screen, list) else [screen]) if n not in connected]
    return [
        Issue(Severity.WARNING, f"Screen {n} is not connected", ELEMENT, "screen", "screen_not_connected")
        for n in missing
    ]


def _position_issues(document: Document, screens: list[Screen]) -> list[Issue]:
    """Warns when a fixed position lies beyond the right or bottom edge of its screen."""
    element = document.element
    screen = element.screen[0] if isinstance(element.screen, list) else element.screen
    screen = 1 if screen is None else screen
    if screen == 0 or not 0 < screen < len(screens):
        return []
    size = {"x": screens[screen].width, "y": screens[screen].height}
    return [
        Issue(Severity.WARNING, f"Position outside screen {screen}", ELEMENT, axis, "position_outside_screen")
        for axis, value in (("x", element.x), ("y", element.y))
        if value is not None and value >= size[axis]
    ]


def _error(message: str, owner: int | None, field: str | None, code: str) -> Issue:
    return Issue(Severity.ERROR, message, owner, field, code)


def _field(loc: tuple) -> str | None:
    return str(loc[0]) if loc else None
