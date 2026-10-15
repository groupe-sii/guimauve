import cv2 as cv
import numpy as np
import pytest

from guimauve.gui.element_editor_next.state import Document
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant


@pytest.fixture
def image_path(tmp_path):
    path = tmp_path / "button.png"
    cv.imwrite(str(path), np.zeros((10, 20, 3), dtype=np.uint8))
    return path


@pytest.fixture
def element(image_path):
    return Element(
        name="button",
        timeout=3,
        variants=[
            ImageVariant(name="light", path=image_path, targets=[Target(name="icon", x=1, y=2)]),
            TextVariant(name="label", text="OK"),
        ],
    )


def test_copy_is_independent_of_element(element):
    document = Document(element)

    document.element.timeout = 10
    document.variants[1].text = "Cancel"

    assert element.timeout == 3
    assert element.variants[1].text == "OK"


def test_code_overrides_are_kept_apart(element):
    document = Document(element, {"timeout": 1})

    assert document.code_overrides == {"timeout": 1}
    assert document.element.timeout == 3


def test_images_are_loaded_at_opening(element):
    document = Document(element)

    assert document.variants[0].image.shape == (10, 20, 3)
    assert element.variants[0].image is None


def test_missing_image_is_left_empty(element, tmp_path):
    element.variants[0].path = tmp_path / "missing.png"

    assert Document(element).variants[0].image is None


def test_keys_are_stable_across_renames(element):
    document = Document(element)
    variant = document.variants[0]
    key = document.key(variant)

    variant.name = "dark"

    assert document.key(variant) == key
    assert document.get(key) is variant


def test_variants_with_same_name_have_different_keys(element):
    element.variants[1].name = "light"
    document = Document(element)

    assert document.key(document.variants[0]) != document.key(document.variants[1])


def test_targets_have_keys(element):
    document = Document(element)
    target = document.variants[0].targets[0]

    assert document.get(document.key(target)) is target


def test_new_object_gets_a_new_key(element):
    document = Document(element)
    known = {document.key(variant) for variant in document.variants}

    assert document.key(TextVariant(name="new", text="Yes")) not in known


def test_removed_variant_keeps_its_key(element):
    document = Document(element)
    variant = document.variants[1]
    key = document.key(variant)

    document.element.variants.remove(variant)

    assert document.get(key) is variant


def test_not_modified_at_opening(element):
    assert not Document(element).is_modified()


def test_field_change_then_revert(element):
    document = Document(element)

    document.element.timeout = 10
    assert document.is_modified()

    document.element.timeout = 3
    assert not document.is_modified()


def test_element_name_change_is_a_modification(element):
    document = Document(element)

    document.element.name = "other"

    assert document.is_modified()


def test_new_image_then_restore_previous(element):
    document = Document(element)
    variant = document.variants[0]
    previous = variant.image

    variant.image = previous.copy()
    assert document.is_modified()

    variant.image = previous
    assert not document.is_modified()


def test_variant_removed_then_reinserted(element):
    document = Document(element)
    variant = document.variants[0]

    document.element.variants.remove(variant)
    assert document.is_modified()

    document.element.variants.insert(0, variant)
    assert not document.is_modified()
