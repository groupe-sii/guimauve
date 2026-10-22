"""Names of new variants, and what the list shows of each variant; without Qt."""

import re
from collections.abc import Collection
from dataclasses import dataclass

from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state.document import Document
from guimauve.gui.element_editor_next.state.validation import Issue, Severity
from guimauve.models.variant import Variant

NEW_NAME = "VARIANT"
COPY_SUFFIX = "_COPY"


@dataclass(frozen=True)
class VariantSummary:
    """What a row of the variant list shows beside the name.

    :param overrides: Number of properties set on the variant, trials included.
    :param errors: Messages of the errors of the variant and its targets.
    :param warnings: Messages of their warnings.
    """

    overrides: int = 0
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def normalize_name(name: str) -> str:
    """Name as Guimauve writes it, like the former editor: upper case, spaces replaced by underscores."""
    return re.sub(r"\s+", "_", name.strip()).upper()


def new_name(taken: Collection[str]) -> str:
    """First free name among VARIANT_1, VARIANT_2…"""
    return _first_free(f"{NEW_NAME}_", taken, start=1)


def copy_name(name: str, taken: Collection[str]) -> str:
    """Name of a copy: NAME_COPY, then NAME_COPY_2, NAME_COPY_3…"""
    base = f"{normalize_name(name)}{COPY_SUFFIX}"
    return base if base not in taken else _first_free(f"{base}_", taken, start=2)


def duplicate(variant: Variant, taken: Collection[str]) -> Variant:
    """Deep copy of a variant, image and targets included, under a free name."""
    copy = variant.model_copy(deep=True)
    copy.name = copy_name(variant.name, taken)
    return copy


def summarize(document: Document, key: int, issues: list[Issue]) -> VariantSummary:
    """Overrides and issues of one variant; the issues of its targets count for the variant."""
    variant = document.get(key)
    fields = type(variant).model_fields
    own = {field for field in FIELDS if field in fields and getattr(variant, field) is not None}
    own |= {field for field in document.trials.variants.get(key, {}) if field in fields}

    owners = {key, *(document.key(target) for target in getattr(variant, "targets", None) or [])}
    mine = [issue for issue in issues if issue.owner in owners]
    return VariantSummary(
        overrides=len(own),
        errors=tuple(issue.message for issue in mine if issue.severity is Severity.ERROR),
        warnings=tuple(issue.message for issue in mine if issue.severity is Severity.WARNING),
    )


def _first_free(prefix: str, taken: Collection[str], start: int) -> str:
    number = start
    while f"{prefix}{number}" in taken:
        number += 1
    return f"{prefix}{number}"
