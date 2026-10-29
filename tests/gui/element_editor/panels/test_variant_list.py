import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget

from guimauve.detection.detector import Match, Point
from guimauve.detection.locate import LocateReport
from guimauve.gui.element_editor_next.panels import VariantList
from guimauve.gui.element_editor_next.panels.variant_list import COLLAPSED_KEY, EMPTY_FIXED, FIXED_NOTE
from guimauve.gui.element_editor_next.state import ELEMENT, Mode, TestResult, TestScope
from guimauve.models.variant import TextVariant


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def show(theme, settings, qtbot):
    def make(store) -> VariantList:
        panel = VariantList(store, theme, settings)
        qtbot.addWidget(panel)
        panel.resize(panel.width(), 600)
        panel.show()
        return panel

    return make


def names(panel) -> list[str]:
    return [row.content().name for row in panel.rows()]


def selected(panel) -> list[bool]:
    return [row.property("selected") for row in panel.rows()]


def test_one_row_per_variant_in_order(store, show, text_variant):
    store.add_variant(text_variant)

    panel = show(store)

    assert names(panel) == ["light", "dark", "label"]
    assert [row.content().number for row in panel.rows()] == [1, 2, 3]


def test_rows_follow_the_store(store, show):
    panel = show(store)

    store.move_variant(store.variant_keys()[1], 0)

    assert names(panel) == ["dark", "light"]
    assert selected(panel) == [False, True]


def test_selection_follows_the_store(store, show):
    panel = show(store)

    store.select(store.variant_keys()[1])

    assert selected(panel) == [False, True]


def test_arrow_keys_select_in_the_store(store, show, qtbot):
    panel = show(store)
    lst = panel.findChild(QListWidget)
    lst.setFocus()

    qtbot.keyClick(lst, Qt.Key.Key_Down)

    assert store.selected_variant == store.variant_keys()[1]
    assert selected(panel) == [False, True]


def test_rename_with_f2(store, show, qtbot):
    panel = show(store)
    lst = panel.findChild(QListWidget)
    lst.setFocus()

    qtbot.keyClick(lst, Qt.Key.Key_F2)
    editor = panel.rows()[0].findChild(QLineEdit, "rename")
    editor.setText("default")
    qtbot.keyClick(editor, Qt.Key.Key_Return)

    assert store.document.variants[0].name == "DEFAULT"
    assert names(panel) == ["DEFAULT", "dark"]


def test_badges_from_the_summary(store, show):
    panel = show(store)

    store.set_field(store.variant_keys()[1], "mouse_speed", 100)

    assert panel.rows()[1].content().summary.overrides == 1


def test_rows_dimmed_with_a_fixed_position(store, show):
    panel = show(store)
    note = panel.findChild(QLabel, "note")

    store.set_field(ELEMENT, "x", 10)

    assert all(row.is_dimmed() for row in panel.rows())
    assert note.text() == FIXED_NOTE


def test_empty_state(make_store, show):
    panel = show(make_store([], x=10))

    assert panel.findChild(QListWidget).isHidden()
    assert not panel.findChild(QLabel, "note").isVisible()
    assert EMPTY_FIXED in [label.text() for label in panel.findChildren(QLabel)]


def test_collapsed_state_is_kept(store, show, settings, theme, qtbot):
    panel = show(store)

    panel.set_collapsed(True)

    assert all(row.collapsed for row in panel.rows())
    assert settings.value(COLLAPSED_KEY, type=bool) is True
    again = VariantList(store, theme, settings)
    qtbot.addWidget(again)
    assert again.is_collapsed()


def test_taken_name_is_refused(make_store, show, qtbot, text_variant):
    store = make_store([TextVariant(name="LIGHT", text="a"), TextVariant(name="DARK", text="b")])
    panel = show(store)
    panel.rows()[0].start_rename()
    editor = panel.rows()[0].findChild(QLineEdit, "rename")

    editor.setText("Dark")
    qtbot.keyClick(editor, Qt.Key.Key_Return)

    assert names(panel) == ["LIGHT", "DARK"]


def test_thumbnail_of_each_image(store, show):
    panel = show(store)

    assert all(row.content().image is not None for row in panel.rows())


def found(panel) -> list[bool]:
    return [row.content().found for row in panel.rows()]


def report(variant: int) -> LocateReport:
    return LocateReport([Match(None, Point(1, 1), 0.9)], match_screens=[1], match_variants=[variant])


def test_the_variant_found_by_the_test_is_marked_in_test_mode(store, show):
    panel = show(store)
    store.set_mode(Mode.TEST)
    assert found(panel) == [False, False]

    store.set_test_result(TestResult(TestScope.ELEMENT, None, report(1), used=0))
    assert found(panel) == [False, True]

    store.set_test_result(TestResult(TestScope.VARIANT, store.variant_keys()[0], report(0), used=0))
    assert found(panel) == [True, False]

    store.set_mode(Mode.EDIT)
    assert found(panel) == [False, False]


def test_a_stale_or_unused_result_marks_nothing(store, show):
    panel = show(store)
    store.set_mode(Mode.TEST)
    store.set_test_result(TestResult(TestScope.ELEMENT, None, report(1), used=None, error="Index 3 out of 1 match"))
    assert found(panel) == [False, False]

    store.set_test_result(TestResult(TestScope.ELEMENT, None, report(1), used=0))
    store.set_field(ELEMENT, "timeout", 9)
    assert found(panel) == [False, False]
