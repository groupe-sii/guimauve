import pytest

from guimauve.enums import OcrFidelity
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant, Variant


def test_bounds_from_image_params_apply_through_image_variant():
    variant = ImageVariant(name="foo", path="x.png", template_confidence_threshold=42)
    errors = variant.validate()
    assert any(e["loc"] == ("template_confidence_threshold",) and "must be" in e["msg"] for e in errors)


def test_target_requires_all_fields():
    with pytest.raises(Exception):
        Target()

    target = Target(name="btn", x=10, y=20)
    assert (target.name, target.x, target.y) == ("btn", 10, 20)


def test_variant_requires_name():
    with pytest.raises(Exception):
        Variant()

    Variant(name="foo")


def test_image_variant_permissive_construction_matches_gui_flow():
    # Mirrors gui/element_editor/widgets/element/variants.py: only `name` is provided up front,
    # `path` is filled in later via setattr as the user edits.
    variant = ImageVariant(name="foo")
    assert variant.path is None
    assert variant.validate()  # incomplete, but construction itself must not raise

    variant.path = "some/image.png"
    assert variant.validate() == []


def test_text_variant_permissive_construction_matches_gui_flow():
    variant = TextVariant(name="foo")
    assert variant.text is None
    assert variant.validate()

    variant.text = "hello"
    assert variant.validate() == []


@pytest.mark.parametrize("value", [None, "", "   "])
def test_image_variant_path_must_not_be_empty(value):
    variant = ImageVariant(name="foo", path=value)
    errors = variant.validate()
    assert any("must not be empty" in e["msg"] for e in errors)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_text_variant_text_must_not_be_empty(value):
    variant = TextVariant(name="foo", text=value)
    errors = variant.validate()
    assert any("must not be empty" in e["msg"] for e in errors)


def test_image_variant_inherits_params_mixins():
    variant = ImageVariant(name="foo", path="x.png", use_template=True, template_confidence_threshold=0.9)
    assert variant.use_template is True
    assert variant.template_confidence_threshold == 0.9


def test_image_variant_enum_by_name_round_trip():
    variant = ImageVariant(name="foo", path="x.png", ocr_fidelity=OcrFidelity.ACCURATE)
    dumped = variant.to_dict()
    assert dumped["ocr_fidelity"] == "ACCURATE"

    loaded = ImageVariant.from_dict(dumped)
    assert loaded.ocr_fidelity is OcrFidelity.ACCURATE


def test_variant_discriminator_defaults_to_image_when_ambiguous():
    # Neither `path` nor `text` present: matches the old smart-union tie-break behaviour.
    element = Element.from_dict({"name": "foo", "variants": [{"name": "bare"}]})
    assert isinstance(element.variants[0], ImageVariant)
