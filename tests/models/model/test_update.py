import enum
from typing import Optional

from pydantic import BaseModel as PydBaseModel

from guimauve.models.model import Model


class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Base(Model):
    name: str = ""
    tags: list = []
    color: Color = Color.RED
    note: Optional[str] = None


class Named(Model):
    name: str = ""  # only field shared with Base


class HasExtra(Model):
    name: str = ""
    items: list = []  # not in Named


class PlainOther(PydBaseModel):
    name: str = "plain"
    whatever: int = 0  # not in Base


class Child(Model):
    items: list = []


class WithChild(Model):
    child: Child = Child()


# --- common fields + purity ---


def test_update_copies_common_fields():
    a = Base(name="old", color=Color.RED)
    b = Base(name="new", color=Color.BLUE)
    r = a.update(b)
    assert r.name == "new"
    assert r.color is Color.BLUE


def test_update_returns_new_instance_and_does_not_mutate_self():
    a = Base(name="old")
    r = a.update(Base(name="new"))
    assert r is not a
    assert a.name == "old"
    assert r.name == "new"


# --- different classes: common fields only ---


def test_update_from_different_class_uses_common_fields_only():
    a = HasExtra(name="x", items=[1])
    b = Named(name="y")
    r = a.update(b)
    assert r.name == "y"  # common field overwritten
    assert r.items == [1]  # self-only field preserved


def test_update_accepts_plain_pydantic_basemodel():
    a = Base(name="x")
    r = a.update(PlainOther(name="y"))
    assert isinstance(r, Base)
    assert r.name == "y"  # only the shared field is used


# --- deep isolation from both self and other ---


def test_update_result_isolated_from_other():
    a = Base(tags=[["a"]])
    b = Base(tags=[["b"]])
    r = a.update(b)  # r.tags is a deep copy of b.tags
    b.tags[0].append("x")  # mutate other's inner list
    assert r.tags == [["b"]]  # result isolated from other (deep)
    r.tags[0].append("y")  # mutate result's inner list
    assert b.tags == [["b", "x"]]  # other isolated from result (deep)


def test_update_result_isolated_from_self_only_fields():
    a = HasExtra(name="x", items=[[1]])
    b = Named(name="y")
    r = a.update(b)  # items preserved from self via deep copy
    a.items[0].append(2)  # mutate self's inner list
    assert r.items == [[1]]  # result isolated from self (deep)


# --- no validation ---


def test_update_does_not_validate():
    a = Base()
    b = Base(color="GREEN")  # deferred: color is the string "GREEN"
    r = a.update(b)
    assert r.color == "GREEN"
    assert not isinstance(r.color, Color)
    assert r.resolve() == []  # resolve coerces afterward
    assert r.color is Color.GREEN


# --- chaining ---


def test_update_chaining_is_pure():
    base = Base(name="base")
    r = base.update(Base(name="a")).update(Base(name="b"))
    assert r.name == "b"
    assert base.name == "base"


# --- deep isolation through a nested submodel field ---


def test_update_deep_copies_nested_submodel():
    a = WithChild(child=Child(items=[1]))
    b = WithChild(child=Child(items=[2]))
    r = a.update(b)  # r.child is a deep copy of b.child
    b.child.items.append(3)  # mutate other's nested submodel
    assert r.child.items == [2]  # result isolated from other (through submodel)
    r.child.items.append(9)  # mutate result's nested submodel
    assert b.child.items == [2, 3]  # other isolated from result
