import numpy as np
import pytest

from guimauve.models.model import Model
from guimauve.models.variant import (
    ImageVariant,
    Target,
    TextVariant,
    Variant,
    VariantUnion,
    _variant_kind,
)

# --- pure functions: no model needed ---


def test_variant_kind_routes_by_structure():
    assert _variant_kind({"path": "/x.png"}) == "image"
    assert _variant_kind({"targets": []}) == "image"
    assert _variant_kind({"text": "hi"}) == "text"


def test_variant_kind_ambiguous_defaults_to_image():
    assert _variant_kind({"name": "z"}) == "image"


def test_variant_kind_by_instance():
    assert _variant_kind(TextVariant(text="hi")) == "text"


# --- path: optional field, but required at resolve + must exist ---


def test_path_none_reports_path_missing():
    errors = ImageVariant().resolve()
    assert any(e["type"] == "path_missing" for e in errors)


def test_path_not_found_reports_error(tmp_path):
    missing = tmp_path / "nope.png"
    errors = ImageVariant(path=missing).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "file_not_found"
    assert errors[0]["loc"] == ("path",)
    assert errors[0]["ctx"]["path"] == str(missing)


def test_path_existing_file_is_valid(real_file):
    assert ImageVariant(path=real_file).resolve() == []


def test_resolve_does_not_load_image(real_file):
    iv = ImageVariant(path=real_file)
    iv.resolve()
    assert iv.image is None  # resolve validates existence only, never loads


# --- targets: list of Target ---


def test_targets_list_resolves(real_file):
    iv = ImageVariant(path=real_file, targets=[{"name": "t1", "x": 0, "y": 0}])
    assert iv.resolve() == []
    assert isinstance(iv.targets[0], Target)
    assert iv.targets[0].name == "t1"


def test_targets_none_is_allowed(real_file):
    assert ImageVariant(path=real_file, targets=None).resolve() == []


@pytest.mark.parametrize("bad", [(10, 20), "oops", 5])
def test_target_wrong_type_reports_error_not_crash(bad, real_file):
    # a non-dict / non-model item in the list must surface a validation error, never crash
    iv = ImageVariant(path=real_file, targets=[bad])
    errors = iv.resolve()  # must not raise
    assert any(e["loc"][:2] == ("targets", 0) for e in errors)


# --- load(): explicit, idempotent, excluded from dump, fails loudly ---


@pytest.fixture
def fake_imread(monkeypatch):
    # stub cv.imread where it's used, in the variant module
    monkeypatch.setattr(
        "guimauve.models.variant.cv.imread",
        lambda p: np.zeros((2, 2, 3), "uint8"),
    )


@pytest.fixture
def fake_imread_fail(monkeypatch):
    # simulate an unreadable/corrupt image: cv.imread returns None
    monkeypatch.setattr("guimauve.models.variant.cv.imread", lambda p: None)


def test_load_populates_image_and_returns_self(fake_imread, real_file):
    iv = ImageVariant(path=real_file)
    result = iv.load()
    assert result is iv  # returns self for chaining
    assert iv.image is not None


def test_load_is_idempotent(fake_imread, real_file):
    iv = ImageVariant(path=real_file).load()
    first = iv.image
    iv.load()
    assert iv.image is first  # not reloaded


def test_image_excluded_from_dump(fake_imread, real_file):
    iv = ImageVariant(path=real_file).load()
    assert "image" not in iv.to_dict()
    assert "image" not in iv.to_dict(json_mode=True)


def test_load_raises_on_unreadable_image(fake_imread_fail, real_file):
    iv = ImageVariant(path=real_file)
    assert iv.resolve() == []  # resolve only checks existence
    with pytest.raises(ValueError):
        iv.load()  # decode failure surfaces here


# --- Variant.name / Target.name: None allowed, blank rejected ---


def test_variant_name_none_is_allowed():
    assert Variant(name=None).resolve() == []


def test_variant_name_blank_is_rejected():
    errors = Variant(name="   ").resolve()
    assert errors[0]["type"] == "empty"
    assert errors[0]["loc"] == ("name",)


def test_target_name_none_is_allowed():
    assert Target(name=None, x=0, y=0).resolve() == []


def test_target_name_blank_is_rejected():
    errors = Target(name="  ", x=0, y=0).resolve()
    assert errors[0]["type"] == "empty"
    assert errors[0]["loc"] == ("name",)


def test_target_requires_x_and_y():
    errors = Target(name="t").resolve()
    types = {(e["type"], e["loc"]) for e in errors}
    assert ("missing", ("x",)) in types
    assert ("missing", ("y",)) in types


# --- TextVariant.text: required + not blank ---


def test_text_variant_requires_text():
    errors = TextVariant().resolve()
    assert any(e["type"] == "missing" and e["loc"] == ("text",) for e in errors)


def test_text_variant_blank_text_is_rejected():
    assert TextVariant(text="").resolve()[0]["type"] == "empty"


def test_text_variant_valid():
    assert TextVariant(text="hello").resolve() == []


# --- discrimination through a real VariantUnion field ---


class _Holder(Model):
    v: VariantUnion


def test_union_routes_dict_with_path_to_image(real_file):
    h = _Holder(v={"path": real_file})
    assert h.resolve() == []
    assert isinstance(h.v, ImageVariant)


def test_union_routes_dict_with_text_to_text():
    h = _Holder(v={"text": "hi"})
    assert h.resolve() == []
    assert isinstance(h.v, TextVariant)


def test_union_image_wins_over_text(real_file):
    # a dict with BOTH path and text -> image branch wins (priority in _variant_kind)
    h = _Holder(v={"path": real_file, "text": "hi"})
    assert h.resolve() == []
    assert isinstance(h.v, ImageVariant)


def test_union_ambiguous_routes_to_image_then_fails_on_missing_path():
    # only `name` -> ambiguous -> image default -> missing path surfaces
    h = _Holder(v={"name": "z"})
    errors = h.resolve()
    assert any(e["type"] == "path_missing" for e in errors)
