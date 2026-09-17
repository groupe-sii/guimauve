from pydantic import PrivateAttr

from guimauve.models.model import Model


class Simple(Model):
    a: int = 0
    b: str = ""


class Required(Model):
    x: int


class Child(Model):
    x: int = 0


class Parent(Model):
    name: str = ""
    child: Child = Child()


class Private(Model):
    _attr: str = PrivateAttr(default="PRIVATE")


# --- Deferred construction: never validates, never raises ---


def test_construction_with_invalid_data_does_not_raise():
    m = Simple(a="not_an_int")
    assert m.a == "not_an_int"  # stored as-is, not coerced


def test_construction_with_missing_required_field_does_not_raise():
    m = Required()  # x missing, no exception at construction time
    assert isinstance(m, Required)


def test_construction_with_valid_data_keeps_values():
    m = Simple(a=5, b="hello")
    assert m.a == 5
    assert m.b == "hello"


# --- resolve: invalid case ---


def test_resolve_reports_invalid_type():
    m = Simple(a="not_an_int")
    errors = m.resolve()
    assert len(errors) == 1
    err = errors[0]
    assert err["loc"] == ("a",)
    assert err["input"] == "not_an_int"
    assert "url" not in err  # include_url=False


def test_resolve_reports_missing_required_field():
    m = Required()
    errors = m.resolve()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("x",)
    assert errors[0]["msg"] == "Field required"


def test_resolve_does_not_adopt_on_error():
    # on failure, the instance must not mutate
    m = Simple(a="not_an_int")
    m.resolve()
    assert m.a == "not_an_int"


# --- resolve: valid case + in-place adoption ---


def test_resolve_returns_empty_list_when_valid():
    m = Simple(a=5, b="ok")
    assert m.resolve() == []


def test_resolve_coerces_in_place_when_valid():
    # "5" is coercible to int by pydantic -> no error,
    # and adoption must replace the value with the coerced int
    m = Simple(a="5")
    assert m.resolve() == []
    assert m.a == 5
    assert isinstance(m.a, int)


def test_resolve_is_idempotent():
    m = Simple(a="5")
    assert m.resolve() == []
    assert m.resolve() == []
    assert m.a == 5


# --- nested models (Model in Model) ---


def test_nested_dict_stays_dict_after_construction():
    # deferred construction does not descend: a submodel given as a dict stays a dict
    p = Parent(child={"x": 1})
    assert isinstance(p.child, dict)


def test_resolve_descends_into_nested_and_reports_nested_loc():
    p = Parent(child={"x": "oops"})
    errors = p.resolve()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("child", "x")


def test_resolve_promotes_nested_dict_to_submodel():
    p = Parent(child={"x": 5})
    assert p.resolve() == []
    assert isinstance(p.child, Child)
    assert p.child.x == 5


def test_resolve_accepts_nested_submodel_instance():
    p = Parent(child=Child(x="7"))  # deferred: x is the string "7"
    assert p.resolve() == []
    assert p.child.x == 7


# --- Resolve keeps private attributes ---


def test_resolve_keeps_private_attributes():
    p = Private()
    p._attr = "CHANGED"
    assert p.resolve() == []
    assert p._attr == "CHANGED"
