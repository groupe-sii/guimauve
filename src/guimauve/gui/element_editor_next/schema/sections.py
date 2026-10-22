"""Sections of the Element tab, in display order, with their fields."""

from dataclasses import dataclass

from pydantic import BaseModel

from guimauve.gui.element_editor_next.schema.fields import FieldDescriptor, enabled_by, no_fixed_position
from guimauve.models.variant import ImageVariant, TextVariant, Variant


@dataclass(frozen=True)
class SectionDescriptor:
    """A collapsible section of the inspector.

    :param key: Identifier of the section.
    :param title: Title shown in the inspector.
    :param fields: Fields in display order.
    :param variant_kind: When set, the section is hidden until the element has a variant of this kind.
    """

    key: str
    title: str
    fields: tuple[FieldDescriptor, ...]
    variant_kind: type[Variant] | None = None


_template = enabled_by("use_template")
_feature = enabled_by("use_feature")
_ocr = enabled_by("use_ocr")
_detection = no_fixed_position


def _feature_setting(key: str, label: str) -> FieldDescriptor:
    """One of the nine feature matching settings, grouped under "Advanced"."""
    return FieldDescriptor(key, label, advanced=True, visible=_feature, effective=_detection)


SECTIONS: tuple[SectionDescriptor, ...] = (
    SectionDescriptor(
        "general",
        "General",
        (
            FieldDescriptor("timeout", "Timeout"),
            FieldDescriptor("target", "Target", effective=_detection),
            FieldDescriptor("find_all", "Find all", effective=_detection),
        ),
    ),
    SectionDescriptor(
        "where_to_search",
        "Where to search",
        (
            FieldDescriptor("screen", "Screen"),
            FieldDescriptor("search_area", "Search area", effective=_detection),
        ),
    ),
    SectionDescriptor(
        "image_detection",
        "Image detection",
        (
            FieldDescriptor("use_template", "Template matching", toggle=True, effective=_detection),
            FieldDescriptor("template_grayscale", "Grayscale", visible=_template, effective=_detection),
            FieldDescriptor("template_confidence_threshold", "Confidence", visible=_template, effective=_detection),
            FieldDescriptor("use_feature", "Feature matching", toggle=True, effective=_detection),
            _feature_setting("feature_n_features", "Features"),
            _feature_setting("feature_contrast_threshold", "Contrast threshold"),
            _feature_setting("feature_edge_threshold", "Edge threshold"),
            _feature_setting("feature_sigma", "Sigma"),
            _feature_setting("feature_lowe_ratio", "Lowe ratio"),
            _feature_setting("feature_min_points", "Minimum points"),
            _feature_setting("feature_ransac_threshold", "RANSAC threshold"),
            _feature_setting("feature_ratio_tolerance", "Ratio tolerance"),
            _feature_setting("feature_size_tolerance", "Size tolerance"),
            FieldDescriptor("use_ocr", "OCR on image", toggle=True, effective=_detection),
            FieldDescriptor("ocr_confidence_threshold", "Confidence", visible=_ocr, effective=_detection),
            FieldDescriptor("ocr_fidelity", "OCR mode", visible=_ocr, effective=_detection),
        ),
        variant_kind=ImageVariant,
    ),
    SectionDescriptor(
        "text_detection",
        "Text detection",
        (
            FieldDescriptor("text_confidence_threshold", "Confidence", effective=_detection),
            FieldDescriptor("text_fidelity", "OCR mode", effective=_detection),
        ),
        variant_kind=TextVariant,
    ),
    SectionDescriptor(
        "multiple_matches",
        "Multiple matches",
        (
            FieldDescriptor("match_sort", "Sort", effective=_detection),
            FieldDescriptor("match_index", "Index", effective=_detection),
        ),
    ),
    SectionDescriptor(
        "mouse",
        "Mouse",
        (
            FieldDescriptor("mouse_speed", "Speed"),
            FieldDescriptor("mouse_direction", "Direction"),
        ),
    ),
    SectionDescriptor(
        "fixed_position",
        "Fixed position",
        (
            FieldDescriptor("x", "X", relative="rel_x", wide=True),
            FieldDescriptor("y", "Y", relative="rel_y", wide=True),
        ),
    ),
)

FIELDS: dict[str, FieldDescriptor] = {
    key: field for section in SECTIONS for field in section.fields for key in field.keys
}
"""Descriptors by field of the models; rel_x and rel_y lead to the descriptor of their axis."""


def override_groups(model: type[BaseModel]) -> list[tuple[str, list[FieldDescriptor]]]:
    """Fields a variant of this type can override, in display order, grouped under a title.

    The title is the section of the field, or the detection method its setting belongs to, e.g. "Template
    matching" for its confidence; a switch of a method stays in its section.
    """
    groups: dict[str, list[FieldDescriptor]] = {}
    for section in SECTIONS:
        title = section.title
        for field in section.fields:
            if field.toggle:
                title = field.label
            if field.key in model.model_fields:
                groups.setdefault(section.title if field.toggle else title, []).append(field)
    return list(groups.items())
