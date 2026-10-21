import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QLabel, QPushButton

from guimauve.gui.element_editor_next.components import Badge, CountBadge, Disclosure, PropertyField, Section
from guimauve.gui.element_editor_next.panels import Inspector
from guimauve.gui.element_editor_next.schema import SECTIONS
from guimauve.gui.element_editor_next.state import ELEMENT, insert


@pytest.fixture
def show(theme, qtbot):
    def make(store) -> Inspector:
        inspector = Inspector(store, theme)
        qtbot.addWidget(inspector)
        inspector.resize(400, 700)
        inspector.show()
        return inspector

    return make


def sections(inspector) -> dict[str, Section]:
    found = inspector.findChildren(Section)
    return {descriptor.key: section for descriptor, section in zip(SECTIONS, found, strict=True)}


def field(inspector, key: str) -> PropertyField:
    return next(f for f in inspector.findChildren(PropertyField) if f.descriptor.key == key)


def counts(section: Section) -> tuple[str, int, int, int]:
    """Counts shown on the badges of a section header: own, code, errors, warnings; 0 when hidden."""
    header = section.findChild(QPushButton, "header", Qt.FindChildOption.FindDirectChildrenOnly)
    (own,) = header.findChildren(Badge)
    code, errors, warnings = header.findChildren(CountBadge)
    shown = [badge.count() if not badge.isHidden() else 0 for badge in (code, errors, warnings)]
    return (own.text() if not own.isHidden() else "0", *shown)


def test_every_section_starts_collapsed(store, show):
    inspector = show(store)

    assert not any(section.is_open() for section in sections(inspector).values())


def test_detection_section_hidden_without_a_variant_of_its_kind(store, show, text_variant):
    inspector = show(store)
    assert not sections(inspector)["image_detection"].isHidden()
    assert sections(inspector)["text_detection"].isHidden()


def test_section_appears_collapsed_with_its_variant(store, show, text_variant):
    inspector = show(store)
    store.execute(insert(store.document, ELEMENT, "variants", text_variant))

    text = sections(inspector)["text_detection"]
    assert not text.isHidden()
    assert not text.is_open()


def test_section_badges_count_own_code_and_issues(make_store, show):
    inspector = show(make_store(timeout=-1, find_all=True))

    assert counts(sections(inspector)["general"]) == ("2", 0, 1, 0)
    assert counts(sections(inspector)["mouse"]) == ("0", 1, 0, 0)


def test_edits_refresh_the_fields(store, show):
    inspector = show(store)

    field(inspector, "timeout").edited.emit(9)

    assert field(inspector, "timeout").findChild(QDoubleSpinBox).value() == 9
    assert counts(sections(inspector)["general"]) == ("1", 0, 0, 0)


def test_advanced_group_shown_with_feature_matching(store, show):
    inspector = show(store)
    group = inspector.findChild(Disclosure)
    assert group.isHidden()

    field(inspector, "use_feature").edited.emit(True)

    assert not group.isHidden()
    assert not group.is_open()
    assert "Advanced, 9 settings" in [label.text() for label in group.findChildren(QLabel)]


def test_fixed_position_disables_detection(make_store, show):
    inspector = show(make_store(x=10))

    assert not field(inspector, "search_area").isEnabled()
    assert field(inspector, "timeout").isEnabled()


def test_fixed_position_has_its_note(store, show):
    inspector = show(store)

    notes = [label.text() for label in sections(inspector)["fixed_position"].findChildren(QLabel)]
    assert "An axis not set keeps the mouse position." in notes


def test_reveal_opens_the_section_and_focuses_the_field(make_store, show, qtbot):
    inspector = show(make_store(use_feature=True))
    inspector.activateWindow()

    assert inspector.reveal(ELEMENT, "feature_sigma")

    assert sections(inspector)["image_detection"].is_open()
    assert inspector.findChild(Disclosure).is_open()
    target = field(inspector, "feature_sigma")
    qtbot.waitUntil(lambda: target.isAncestorOf(QApplication.focusWidget()))


def test_reveal_of_a_hidden_field_does_nothing(store, show):
    inspector = show(store)

    assert not inspector.reveal(ELEMENT, "feature_sigma")  # feature matching is off
    assert not inspector.reveal(ELEMENT, "text_fidelity")  # no text variant
    assert not inspector.reveal(1, "timeout")  # a variant: not this tab
    assert not any(section.is_open() for section in sections(inspector).values())


def test_reveal_an_axis_by_its_relative_field(store, show):
    inspector = show(store)

    assert inspector.reveal(ELEMENT, "rel_y")
    assert sections(inspector)["fixed_position"].is_open()
