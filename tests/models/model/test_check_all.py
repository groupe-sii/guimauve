import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from guimauve.models.model import check_all


def _ok():
    pass


def _bad(type_="err", msg="something wrong"):
    def check():
        raise PydanticCustomError(type_, msg)

    return check


def test_check_all_no_checks_does_not_raise():
    check_all()  # nothing to check


def test_check_all_all_passing_does_not_raise():
    check_all(_ok, _ok)


def test_check_all_single_failure_raises_validation_error():
    with pytest.raises(ValidationError) as exc:
        check_all(_ok, _bad("e1", "first"))
    errors = exc.value.errors(include_url=False)
    assert len(errors) == 1
    assert errors[0]["type"] == "e1"
    assert errors[0]["msg"] == "first"


def test_check_all_aggregates_multiple_failures():
    with pytest.raises(ValidationError) as exc:
        check_all(_bad("e1", "first"), _ok, _bad("e2", "second"))
    errors = exc.value.errors(include_url=False)
    assert len(errors) == 2
    assert [e["type"] for e in errors] == ["e1", "e2"]


def test_check_all_interpolates_ctx_in_message():
    def check():
        raise PydanticCustomError("e", "value is {n}", {"n": 42})

    with pytest.raises(ValidationError) as exc:
        check_all(check)
    assert exc.value.errors()[0]["msg"] == "value is 42"


def test_check_all_non_custom_exception_propagates():
    def boom():
        raise ValueError("not a PydanticCustomError")

    # not swallowed nor wrapped: it bubbles up as-is
    with pytest.raises(ValueError):
        check_all(boom)
