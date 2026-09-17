import enum

from guimauve.models.model import Model, ModelError


def test_model_error_stores_errors():
    errors = [{"loc": ("a",), "msg": "bad", "input": 1}]
    err = ModelError("Foo", errors)
    assert err.errors is errors


def test_model_error_is_value_error():
    assert issubclass(ModelError, ValueError)


def test_model_error_singular_title():
    err = ModelError("Foo", [{"loc": ("a",), "msg": "bad", "input": None}])
    assert "(1 error)" in str(err)


def test_model_error_plural_title():
    errors = [
        {"loc": ("a",), "msg": "bad", "input": None},
        {"loc": ("b",), "msg": "worse", "input": None},
    ]
    assert "(2 errors)" in str(ModelError("Foo", errors))


def test_model_error_joins_loc_with_arrow():
    err = ModelError("Foo", [{"loc": ("a", "b", "c"), "msg": "bad", "input": None}])
    assert "a -> b -> c: bad" in str(err)


def test_model_error_non_string_loc_elements():
    err = ModelError("Foo", [{"loc": ("items", 0), "msg": "bad", "input": None}])
    assert "items -> 0: bad" in str(err)


def test_model_error_empty_loc_shows_root():
    err = ModelError("Foo", [{"loc": (), "msg": "root problem", "input": None}])
    assert "<root>: root problem" in str(err)


def test_model_error_renders_input_when_present():
    err = ModelError("Foo", [{"loc": ("a",), "msg": "bad", "input": "x"}])
    assert "bad (got 'x')" in str(err)


def test_model_error_omits_input_when_none():
    err = ModelError("Foo", [{"loc": ("a",), "msg": "bad", "input": None}])
    assert "(got" not in str(err)


def test_model_error_renders_falsy_non_none_input():
    # input=0 is falsy but not None -> must still render (guards against a truthiness check)
    err = ModelError("Foo", [{"loc": ("a",), "msg": "bad", "input": 0}])
    assert "(got 0)" in str(err)


# =========================
# integration: resolve() -> ModelError
# =========================


def test_model_error_from_real_resolve():
    class Color(enum.Enum):
        RED = 1

    class Doc(Model):
        count: int = 0
        color: Color = Color.RED

    m = Doc(count="oops", color="PURPLE")
    errors = m.resolve()
    rendered = str(ModelError("Doc", errors))
    assert "Invalid Doc (2 errors):" in rendered
    assert "count:" in rendered
    assert "color: Input should be a valid Color (got 'PURPLE')" in rendered
