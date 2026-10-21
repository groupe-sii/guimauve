from types import SimpleNamespace

import pytest

from guimauve.controller import Controller
from guimauve.enums import OcrFidelity
from guimauve.gui.element_editor_next.state import Document, Source, Trials, resolve, resolve_element, resolve_variant
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import ImageVariant, TextVariant


@pytest.fixture
def default():
    return Parameters().default


@pytest.fixture
def element():
    return Element(
        name="button",
        mouse_speed=200,
        variants=[
            TextVariant(name="label", text="OK"),
            TextVariant(name="short", text="O", mouse_speed=400),
        ],
    )


@pytest.fixture
def document(element):
    return Document(element, {"mouse_speed": 300})


def test_default_only(document, default):
    resolution = resolve("text_confidence_threshold", document, default)

    assert resolution.source is Source.DEFAULT
    assert resolution.layers == {Source.DEFAULT: default.text_confidence_threshold}


def test_element_wins_over_default(document, default):
    document.element.timeout = 9

    assert resolve("timeout", document, default).source is Source.ELEMENT


def test_code_wins_over_element(document, default):
    resolution = resolve("mouse_speed", document, default)

    assert (resolution.value, resolution.source) == (300, Source.CODE)
    assert resolution.layers == {Source.DEFAULT: 0, Source.ELEMENT: 200, Source.CODE: 300}


def test_code_can_be_excluded(document, default):
    resolution = resolve("mouse_speed", document, default, include_code=False)

    assert (resolution.value, resolution.source) == (200, Source.ELEMENT)


def test_element_trial_wins_over_code(document, default):
    trials = Trials(element={"mouse_speed": 350})

    assert resolve("mouse_speed", document, default, trials=trials).value == 350


def test_variant_wins_over_element_trial(document, default):
    variant = document.variants[1]
    trials = Trials(element={"mouse_speed": 350})

    resolution = resolve("mouse_speed", document, default, variant, trials)

    assert (resolution.value, resolution.source) == (400, Source.VARIANT)


def test_variant_trial_wins_over_everything(document, default):
    variant = document.variants[1]
    trials = Trials(element={"mouse_speed": 350}, variants={document.key(variant): {"mouse_speed": 450}})

    resolution = resolve("mouse_speed", document, default, variant, trials)

    assert (resolution.value, resolution.source) == (450, Source.VARIANT_TRIAL)


def test_variant_without_value_inherits_element_chain(document, default):
    resolution = resolve("mouse_speed", document, default, document.variants[0])

    assert (resolution.value, resolution.source) == (300, Source.CODE)


def test_element_field_ignores_variant_layers(document, default):
    variant = document.variants[0]
    trials = Trials(variants={document.key(variant): {"timeout": 1}})

    assert resolve("timeout", document, default, variant, trials).source is Source.DEFAULT


def test_field_missing_on_variant_type(default):
    document = Document(Element(name="e", variants=[ImageVariant(name="image")]))

    resolution = resolve("text_fidelity", document, default, document.variants[0])

    assert resolution.source is Source.DEFAULT


def test_undefined_everywhere(document, default):
    resolution = resolve("x", document, default)

    assert (resolution.value, resolution.source, resolution.layers) == (None, None, {})


def test_resolve_element_matches_controller(element, default):
    overrides = {"mouse_speed": 300, "text_fidelity": OcrFidelity.ACCURATE}
    expected = Controller._update(SimpleNamespace(parameters=Parameters()), element(**overrides))

    resolved = resolve_element(Document(element, overrides), default)

    assert resolved.to_dict() == expected.to_dict()


def test_resolve_variant_applies_trials_without_touching_document(document, default):
    variant = document.variants[0]
    trials = Trials(element={"timeout": 1}, variants={document.key(variant): {"text_confidence_threshold": 0.5}})

    resolved = resolve_variant(document, default, variant, trials)

    assert resolved.text_confidence_threshold == 0.5
    assert resolved.mouse_speed == 300
    assert variant.text_confidence_threshold is None
    assert document.element.timeout is None
    assert not document.is_modified()
