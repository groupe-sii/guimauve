import pytest

from guimauve.gui.element_editor_next.state import ELEMENT, Document, Group, SetValue, insert, move, remove
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant


@pytest.fixture
def document():
    return Document(
        Element(
            name="button",
            timeout=3,
            variants=[
                ImageVariant(name="light", targets=[Target(name="icon", x=1, y=2)]),
                TextVariant(name="label", text="OK"),
                TextVariant(name="short", text="O"),
            ],
        )
    )


def keys(document):
    return [document.key(variant) for variant in document.variants]


def test_set_element_field(document):
    command = SetValue(ELEMENT, "timeout", 10)

    command.do(document)
    assert document.element.timeout == 10

    command.undo(document)
    assert document.element.timeout == 3


def test_set_variant_and_target_fields(document):
    variant = document.variants[1]
    target = document.variants[0].targets[0]

    SetValue(document.key(variant), "name", "renamed").do(document)
    SetValue(document.key(target), "x", 5).do(document)

    assert (variant.name, target.x) == ("renamed", 5)


def test_redo_keeps_opening_value(document):
    command = SetValue(ELEMENT, "timeout", 10)

    command.do(document)
    command.undo(document)
    command.do(document)
    command.undo(document)

    assert document.element.timeout == 3


def test_same_gesture_on_same_field_merges(document):
    first = SetValue(ELEMENT, "timeout", 4, gesture=1)
    second = SetValue(ELEMENT, "timeout", 5, gesture=1)

    first.do(document)
    second.do(document)

    assert first.merge(second)
    first.undo(document)
    assert document.element.timeout == 3


@pytest.mark.parametrize(
    "other",
    [
        SetValue(ELEMENT, "timeout", 5, gesture=2),
        SetValue(ELEMENT, "mouse_speed", 5, gesture=1),
        SetValue(ELEMENT, "timeout", 5),
    ],
)
def test_other_commands_do_not_merge(other):
    assert not SetValue(ELEMENT, "timeout", 4, gesture=1).merge(other)


def test_command_without_gesture_never_merges():
    assert not SetValue(ELEMENT, "timeout", 4).merge(SetValue(ELEMENT, "timeout", 5))


def test_group_undoes_in_reverse_order(document):
    group = Group([SetValue(ELEMENT, "timeout", 4), SetValue(ELEMENT, "timeout", 5)])

    group.do(document)
    assert document.element.timeout == 5

    group.undo(document)
    assert document.element.timeout == 3


def test_insert_at_end_keeps_existing_keys(document):
    before = keys(document)
    variant = TextVariant(name="new", text="Yes")

    insert(document, ELEMENT, "variants", variant).do(document)

    assert keys(document) == [*before, document.key(variant)]


def test_insert_at_index(document):
    variant = TextVariant(name="new", text="Yes")

    insert(document, ELEMENT, "variants", variant, 1).do(document)

    assert document.variants[1] is variant


def test_insert_into_empty_list():
    document = Document(Element(name="button", variants=[ImageVariant(name="light")]))
    variant = document.variants[0]

    insert(document, document.key(variant), "targets", Target(name="t", x=0, y=0)).do(document)

    assert len(variant.targets) == 1


def test_remove_then_undo_restores_same_objects(document):
    previous = document.element.variants
    command = remove(document, ELEMENT, "variants", document.key(document.variants[1]))

    command.do(document)
    assert [variant.name for variant in document.variants] == ["light", "short"]

    command.undo(document)
    assert document.element.variants is previous
    assert not document.is_modified()


def test_removing_last_item_leaves_none(document):
    variant = document.variants[0]

    remove(document, document.key(variant), "targets", document.key(variant.targets[0])).do(document)

    assert variant.targets is None


def test_move(document):
    last = document.variants[2]

    move(document, ELEMENT, "variants", document.key(last), 0).do(document)

    assert [variant.name for variant in document.variants] == ["short", "light", "label"]


def test_list_is_replaced_not_mutated(document):
    previous = document.element.variants
    names = [variant.name for variant in previous]

    insert(document, ELEMENT, "variants", TextVariant(name="new", text="Yes")).do(document)

    assert [variant.name for variant in previous] == names
