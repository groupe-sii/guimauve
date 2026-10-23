import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QToolButton

from guimauve.gui.element_editor_next.components import PropertyField
from guimauve.gui.element_editor_next.panels import VariantInspector
from guimauve.gui.element_editor_next.panels.variant_inspector import IMAGE_CENTER, WHOLE_IMAGE
from guimauve.models.area import Area


@pytest.fixture
def show(theme, qtbot):
    def make(store) -> VariantInspector:
        inspector = VariantInspector(store, theme)
        qtbot.addWidget(inspector)
        inspector.resize(400, 800)
        inspector.show()
        return inspector

    return make


def light(store) -> int:
    return store.variant_keys()[0]


def fields(inspector) -> list[str]:
    return [f.descriptor.key for f in inspector.findChildren(PropertyField) if f.isVisible()]


def target_names(inspector) -> list[str]:
    return [e.text() for e in inspector.findChildren(QLineEdit) if e.placeholderText() and e.isVisible()]


def override_menu(inspector) -> list[str]:
    menu = inspector.findChild(QPushButton, "override").menu()
    menu.aboutToShow.emit()
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def test_shows_the_selected_variant(store, show, qtbot):
    inspector = show(store)

    assert inspector.findChild(QLineEdit, "name").text() == "light"
    assert inspector.findChild(QLabel, "kind").text() == "Image · 120 × 40 px"
    store.select(store.variant_keys()[1])
    qtbot.wait(1)  # rows replaced: the new ones are shown and the old ones deleted by the event loop
    assert inspector.findChild(QLineEdit, "name").text() == "dark"
    assert target_names(inspector) == ["icon"]


def test_rename_the_variant(store, show):
    inspector = show(store)
    name = inspector.findChild(QLineEdit, "name")

    name.setText("dark theme")
    name.editingFinished.emit()

    assert store.document.variants[0].name == "DARK_THEME"
    assert name.text() == "DARK_THEME"


@pytest.mark.parametrize("text", [" ", "dark"])
def test_refused_name_is_put_back(store, show, text):
    store.rename_variant(store.variant_keys()[1], "DARK")
    inspector = show(store)
    name = inspector.findChild(QLineEdit, "name")

    name.setText(text)
    name.editingFinished.emit()

    assert name.text() == "light"
    assert store.document.variants[0].name == "light"


def test_targets_renamed_and_deleted(store, show):
    inspector = show(store)
    editor = next(e for e in inspector.findChildren(QLineEdit) if e.text() == "arrow")

    editor.setText("")
    editor.editingFinished.emit()
    assert store.document.variants[0].targets[1].name is None

    delete = [b for b in inspector.findChildren(QToolButton) if b.toolTip() == "Delete target" and b.isVisible()]
    delete[0].click()
    assert [t.name for t in store.document.variants[0].targets] == [None]


def test_default_target_choices(store, show):
    inspector = show(store)
    combo = inspector.findChild(QComboBox, "defaultTarget")

    assert [combo.itemText(i) for i in range(combo.count())] == [IMAGE_CENTER, "icon", "arrow"]
    combo.activated.emit(2)
    assert store.document.variants[0].default_target == "arrow"
    assert combo.currentText() == "arrow"


def test_match_area_summary_and_reset(store, show):
    store.set_field(light(store), "match_area", Area(left=24, top=8, right=96, bottom=32))
    inspector = show(store)
    label = inspector.findChild(QLabel, "matchArea")

    assert label.text() == "24, 8 to 96, 32 · 72 × 24"
    inspector.findChild(QToolButton, "resetMatchArea").click()
    assert label.text() == WHOLE_IMAGE
    assert store.document.variants[0].match_area is None


def test_text_variant_has_no_image_part(store, show, text_variant):
    store.add_variant(text_variant)
    inspector = show(store)

    assert inspector.findChild(QLabel, "kind").text() == "Text · “Sign in”"
    assert (
        inspector.findChild(QComboBox, "defaultTarget").isHidden()
        or not inspector.findChild(QComboBox, "defaultTarget").isVisible()
    )


def test_override_a_setting_adds_its_field(store, show):
    inspector = show(store)
    assert fields(inspector) == []

    store.override(light(store), "match_index", "Index")

    assert fields(inspector) == ["match_index"]
    assert "Index" not in override_menu(inspector)


def test_reset_removes_the_override(store, show):
    store.set_field(light(store), "match_index", 2)
    inspector = show(store)
    field = inspector.findChildren(PropertyField)[0]

    field.reset_requested.emit()

    assert store.document.variants[0].match_index is None
    assert fields(inspector) == []


def test_edit_an_override(store, show):
    store.set_field(light(store), "match_index", 2)
    inspector = show(store)

    inspector.findChildren(PropertyField)[0].edited.emit(4)

    assert store.document.variants[0].match_index == 4


def test_override_menu_lists_the_settings_of_the_variant(store, show, text_variant):
    inspector = show(store)

    image = override_menu(inspector)
    store.add_variant(text_variant)
    text = override_menu(inspector)

    assert "Template matching" in image and "Timeout" not in image
    assert "Template matching" not in text and "Speed" in text


def test_override_menu_adds_the_override(store, show):
    inspector = show(store)
    menu = inspector.findChild(QPushButton, "override").menu()
    menu.aboutToShow.emit()

    next(a for a in menu.actions() if a.text() == "Speed").trigger()

    assert store.document.variants[0].mouse_speed == 500  # the value it inherited, from the code


def test_override_of_a_method_turned_off_stays_visible(store, show):
    store.set_field(light(store), "template_grayscale", True)
    store.set_field(light(store), "use_template", False)

    assert set(fields(show(store))) == {"use_template", "template_grayscale"}


def test_nothing_without_variant(make_store, show):
    inspector = show(make_store([], x=1))

    assert not inspector.widget().isVisible()


def target_rows(inspector):
    return [frame for frame in inspector.findChildren(QFrame) if frame.property("targetRow") and frame.isVisible()]


def test_selected_target_row_is_highlighted(store, show):
    inspector = show(store)
    second = store.document.key(store.document.variants[0].targets[1])

    store.select(light(store), second)

    assert [row.property("selected") for row in target_rows(inspector)] == [False, True]


def test_click_on_a_target_row_selects_the_target(store, show, qtbot):
    inspector = show(store)

    qtbot.mouseClick(target_rows(inspector)[1], Qt.MouseButton.LeftButton)

    assert store.selected_target == store.document.key(store.document.variants[0].targets[1])


def test_editing_a_target_name_selects_the_target(store, show):
    inspector = show(store)

    QApplication.sendEvent(target_rows(inspector)[0].findChild(QLineEdit), QFocusEvent(QEvent.Type.FocusIn))

    assert store.selected_target == store.document.key(store.document.variants[0].targets[0])
