import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QLabel, QPushButton

from guimauve.gui.element_editor_next.components import Badge, CountBadge, Disclosure, PropertyField, Section
from guimauve.gui.element_editor_next.panels import FieldBinding, Inspector
from guimauve.gui.element_editor_next.schema import FIELDS, SECTIONS
from guimauve.gui.element_editor_next.state import ELEMENT, Mode, insert
from guimauve.gui.element_editor_next.theme import METRICS
from guimauve.models.area import Area


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


def test_never_scrolls_sideways(store, show):
    inspector = show(store)

    assert inspector.horizontalScrollBarPolicy() is Qt.ScrollBarPolicy.ScrollBarAlwaysOff


class _Picker:
    """Picks the point it is given, at once."""

    def __init__(self, point=(1280, 24), unavailable=None):
        self.point, self.unavailable = point, unavailable
        self.screens = []

    def pick_point(self, screen, done):
        self.screens.append(screen)
        done(*self.point)


def test_pick_on_screen_sets_both_axes_at_once(store, theme, qtbot):
    store.set_fields(ELEMENT, {"rel_x": 5}, "X")
    picker = _Picker()
    inspector = Inspector(store, theme, picker)
    qtbot.addWidget(inspector)

    inspector.findChild(QPushButton, "pickOnScreen").click()

    element = store.document.element
    assert (element.x, element.rel_x, element.y, element.rel_y) == (1280, None, 24, None)
    assert store.undo_label == "Pick on screen"
    store.undo()
    assert store.document.element.rel_x == 5


def test_pick_on_screen_follows_the_screen(store, theme, qtbot):
    store.set_field(ELEMENT, "screen", 0)
    picker = _Picker()
    inspector = Inspector(store, theme, picker)
    qtbot.addWidget(inspector)

    inspector.findChild(QPushButton, "pickOnScreen").click()

    assert picker.screens == [0]


def test_pick_on_screen_unavailable(store, theme, qtbot):
    inspector = Inspector(store, theme, _Picker(unavailable="No display"))
    qtbot.addWidget(inspector)

    button = inspector.findChild(QPushButton, "pickOnScreen")

    assert not button.isEnabled()
    assert button.toolTip() == "No display"


def test_no_pick_on_screen_without_picker(store, show):
    assert show(store).findChild(QPushButton, "pickOnScreen") is None


class _AreaPicker:
    """Draws the area it is given, at once."""

    unavailable = None

    def __init__(self, area):
        self.area, self.screens = area, []

    def pick_area(self, screen, done):
        self.screens.append(screen)
        done(self.area)


def test_draw_the_search_area(store, theme, qtbot):
    area = Area(left=10, top=20, right=300, bottom=200)
    store.set_field(ELEMENT, "screen", 2)
    picker = _AreaPicker(area)
    inspector = Inspector(store, theme, picker)
    qtbot.addWidget(inspector)

    inspector.findChild(QPushButton, "drawSearchArea").click()

    assert store.document.element.search_area == area
    assert picker.screens == [2]


def test_draw_the_search_area_of_a_variant(store, theme, qtbot):
    area = Area(left=1, top=2, right=30, bottom=40)
    key = store.variant_keys()[0]
    binding = FieldBinding(store, FIELDS["search_area"], theme, owner=key, picker=_AreaPicker(area))
    qtbot.addWidget(binding.field)
    binding.refresh({})

    binding.field.editor.draw.click()

    assert store.document.variants[0].search_area == area
    assert store.document.element.search_area is None


def test_label_on_the_first_line_of_a_taller_editor(store, theme, qtbot):
    inspector = Inspector(store, theme, _AreaPicker(None))
    qtbot.addWidget(inspector)
    inspector.resize(400, 1200)
    inspector.show()
    for section in inspector.findChildren(Section):
        section.set_open(True)
    search_area = field(inspector, "search_area")
    qtbot.waitUntil(lambda: search_area.isVisible())

    label = next(label for label in search_area.findChildren(QLabel) if label.property("fieldLabel"))
    combo = search_area.editor.findChild(QComboBox)

    assert search_area.height() > METRICS.control_height  # the button below the list
    middle = label.mapTo(search_area, label.rect().center()).y()
    assert combo.mapTo(search_area, combo.rect().topLeft()).y() == 0
    assert middle <= METRICS.control_height / 2 + 1  # on the line of the list, not the middle of the field


def test_test_mode_shows_only_the_settings_of_the_search(store, show):
    inspector = show(store)
    for section in sections(inspector).values():
        section.set_open(True)

    store.set_mode(Mode.TEST)
    shown = sections(inspector)
    assert not shown["mouse"].isVisible() and not shown["fixed_position"].isVisible()
    assert not field(inspector, "timeout").isVisible()
    assert field(inspector, "target").isVisible() and field(inspector, "screen").isVisible()

    store.set_mode(Mode.EDIT)
    assert shown["mouse"].isVisible() and field(inspector, "timeout").isVisible()
