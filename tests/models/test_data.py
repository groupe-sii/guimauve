import pytest

from guimauve.models.data import Data


@pytest.mark.parametrize("field", ["elements", "replays"])
def test_empty_dict_is_rejected(field):
    errors = Data(**{field: {}}).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "empty"
    assert errors[0]["loc"] == (field,)


def test_none_is_allowed():
    assert Data().resolve() == []


def test_empty_data_is_valid():
    # neither elements nor replays -> currently valid (no "at least one" rule)
    assert Data(elements=None, replays=None).resolve() == []


def test_key_injected_as_name():
    data = Data(elements={"LOGIN": {"x": 5}})
    assert data.resolve() == []
    assert data.elements["LOGIN"].name == "LOGIN"


def test_valid_nested_element_accepted():
    assert Data(elements={"A": {"x": 5}}).resolve() == []


def test_invalid_keys(real_file):
    errors = Data(elements={"A": {"x": 5}}).resolve()
    assert not errors

    errors = Data(elements={"a": {"x": 5}}).resolve()
    assert any(e["type"] == "bad_name" and e["loc"] == ("elements",) for e in errors)

    errors = Data(replays={"123": {"path": real_file}}).resolve()
    print(errors)
    assert any(e["type"] == "bad_name" and e["loc"] == ("replays",) for e in errors)


def test_nested_element_error_surfaces_with_loc():
    # an element with no locator -> its error bubbles up under the element's key
    errors = Data(elements={"A": {}}).resolve()
    assert any(e["type"] == "no_locator" and e["loc"][:2] == ("elements", "A") for e in errors)


def test_nested_field_error_surfaces_with_loc():
    # a bad type on a nested field bubbles up at the deep loc
    errors = Data(elements={"A": {"x": "oops"}}).resolve()
    assert any(e["loc"] == ("elements", "A", "x") for e in errors)
