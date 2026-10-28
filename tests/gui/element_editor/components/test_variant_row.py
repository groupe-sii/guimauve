import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLineEdit

from guimauve.gui.element_editor_next.components import Dot, IconLabel, RowContent, Thumbnail, VariantKind, VariantRow
from guimauve.gui.element_editor_next.state import VariantSummary
from guimauve.gui.element_editor_next.theme import Icon


@pytest.fixture
def make_row(theme, qtbot):
    def make(content: RowContent, collapsed=False) -> VariantRow:
        row = VariantRow(theme, collapsed)
        qtbot.addWidget(row)
        row.set_content(content)
        row.resize(224, row.sizeHint().height())
        row.show()
        return row

    return make


def badges(row) -> dict[str, bool]:
    errors, warnings = [label for label in row.findChildren(IconLabel) if label.objectName() != "grip"][1:]
    (dot,) = [dot for dot in row.findChildren(Dot) if dot.objectName() != "found"]
    return {"errors": not errors.isHidden(), "warnings": not warnings.isHidden(), "overrides": not dot.isHidden()}


def test_badges_show_only_what_the_variant_has(make_row):
    summary = VariantSummary(overrides=2, errors=("No image",))

    row = make_row(RowContent(1, "light", VariantKind.IMAGE, summary=summary))

    assert badges(row) == {"errors": True, "warnings": False, "overrides": True}
    assert row.findChildren(Dot)[0].toolTip() == "2 overrides"


def test_found_dot(make_row):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE, found=True))

    dot = next(dot for dot in row.findChildren(Dot) if dot.objectName() == "found")
    assert not dot.isHidden() and dot.toolTip() == "Found by the last test"


def test_badge_details_in_the_tooltips(make_row):
    summary = VariantSummary(warnings=("Target outside the image", "Screen 3 is not connected"))

    row = make_row(RowContent(1, "light", VariantKind.IMAGE, summary=summary))

    warnings = [label for label in row.findChildren(IconLabel) if label.objectName() != "grip"][2]
    assert warnings.toolTip() == "Target outside the image\nScreen 3 is not connected"


def test_thumbnail_of_a_text_variant_shows_its_text(make_row):
    row = make_row(RowContent(4, "label", VariantKind.TEXT, text="Sign in"))

    assert not row.thumbnail.is_missing()


def test_thumbnail_missing_without_image(make_row):
    assert make_row(RowContent(1, "hover", VariantKind.IMAGE)).thumbnail.is_missing()


@pytest.mark.parametrize(("kind", "icon"), [(VariantKind.IMAGE, Icon.IMAGE), (VariantKind.TEXT, Icon.TEXT_INPUT)])
def test_missing_content_has_the_icon_of_its_kind(make_row, kind, icon):
    row = make_row(RowContent(4, "label", kind))

    assert row.thumbnail.is_missing()
    assert row.thumbnail.missing_icon() is icon


def test_thumbnail_box_leaves_a_padding():
    assert Thumbnail.box(QSize(52, 34)) == QSize(44, 26)


def test_selected_row_is_styled_by_property(make_row):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE, image=QImage(10, 10, QImage.Format.Format_RGB888)))

    row.set_selected(True)

    assert row.property("selected") is True


def test_dimmed_row(make_row):
    assert make_row(RowContent(1, "light", VariantKind.IMAGE, dimmed=True)).is_dimmed()
    assert not make_row(RowContent(1, "light", VariantKind.IMAGE)).is_dimmed()


def test_rename_with_enter(make_row, qtbot):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE))
    row.start_rename()
    editor = row.findChild(QLineEdit, "rename")
    assert row.is_renaming() and editor.selectedText() == "light"

    editor.setText("default")
    with qtbot.waitSignal(row.renamed) as signal:
        qtbot.keyClick(editor, Qt.Key.Key_Return)

    assert signal.args == ["default"]
    assert not row.is_renaming()


@pytest.mark.parametrize("text", ["light", "  ", ""])
def test_rename_ignores_an_empty_or_same_name(make_row, qtbot, text):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE))
    row.start_rename()
    row.findChild(QLineEdit, "rename").setText(text)

    with qtbot.assertNotEmitted(row.renamed):
        qtbot.keyClick(row.findChild(QLineEdit, "rename"), Qt.Key.Key_Return)


def test_rename_cancelled_with_escape(make_row, qtbot):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE))
    row.start_rename()
    editor = row.findChild(QLineEdit, "rename")
    editor.setText("default")

    with qtbot.assertNotEmitted(row.renamed):
        qtbot.keyClick(editor, Qt.Key.Key_Escape)
    assert not row.is_renaming()


def test_collapsed_row_sums_up_with_one_dot(make_row):
    summary = VariantSummary(overrides=1, warnings=("Target outside the image",))

    row = make_row(RowContent(2, "dark", VariantKind.IMAGE, summary=summary), collapsed=True)

    (dot,) = row.findChildren(Dot)
    assert not dot.isHidden()
    assert row.toolTip() == "dark\nTarget outside the image\n1 override"
    row.start_rename()
    assert not row.is_renaming()


def test_grip_shows_the_drag(make_row):
    row = make_row(RowContent(1, "light", VariantKind.IMAGE))

    assert row.grip.cursor().shape() == Qt.CursorShape.OpenHandCursor
