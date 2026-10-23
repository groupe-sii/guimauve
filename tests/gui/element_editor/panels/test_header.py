import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton, QWidgetAction

from guimauve.gui.element_editor_next.components import CHECK, Badge, CenteredLabel, CountBadge
from guimauve.gui.element_editor_next.contract import ResumeMode
from guimauve.gui.element_editor_next.panels import Header
from guimauve.gui.element_editor_next.panels import header as header_module
from guimauve.gui.element_editor_next.state import ELEMENT
from guimauve.gui.element_editor_next.theme import ThemeChoice


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def make_header(store, theme, settings, qtbot):
    def make(from_run=True, on=None) -> Header:
        header = Header(on or store, theme, settings, from_run)
        qtbot.addWidget(header)
        header.show()
        return header

    return make


def buttons(header) -> dict[str, QPushButton]:
    return {button.text(): button for button in header.findChildren(QPushButton)}


def resume_actions(header) -> dict[str, object]:
    menu = buttons(header)["Now"].menu()
    return {action.text(): action for action in menu.actions() if action.isCheckable()}


def test_shows_the_element_name(make_header):
    header = make_header()

    assert "button" in [label.text() for label in header.findChildren(QLabel)]


def test_labels_during_a_run(make_header):
    assert {"Skip", "Save and resume", "Now"} <= buttons(make_header()).keys()


def test_labels_from_the_cli(make_header):
    shown = buttons(make_header(from_run=False))

    assert {"Cancel", "Save"} <= shown.keys()
    assert "Now" not in shown


def test_save_and_skip_are_requested(make_header, qtbot):
    header = make_header()

    with qtbot.waitSignal(header.save_requested):
        buttons(header)["Save and resume"].click()
    with qtbot.waitSignal(header.skip_requested):
        buttons(header)["Skip"].click()


def test_save_blocked_while_an_error_remains(store, make_header):
    header = make_header()
    store.set_field(ELEMENT, "timeout", -1)

    save = buttons(header)["Save and resume"]
    assert not save.isEnabled()
    assert save.toolTip() == "Fix 1 issue to save"


def counts(header) -> tuple[str, int, int, int]:
    """Badges next to the name: own, code, errors, warnings; 0 when hidden."""
    (own,) = header.findChildren(Badge)
    code, errors, warnings = header.findChildren(CountBadge)
    shown = [badge.count() if not badge.isHidden() else 0 for badge in (code, errors, warnings)]
    return (own.text() if not own.isHidden() else "0", *shown)


def test_badges_sum_up_the_element(make_store, make_header):
    store = make_store(timeout=-1, find_all=True, screen=3, x=10, rel_x=None)

    assert counts(make_header(on=store)) == ("4", 2, 1, 1)


def test_badges_hidden_at_zero(make_store, make_header):
    assert counts(make_header(on=make_store(code={}))) == ("0", 0, 0, 0)


def test_badges_follow_the_edits(store, make_header):
    header = make_header()
    store.set_field(ELEMENT, "timeout", -1)

    assert counts(header) == ("1", 2, 1, 0)


def test_undo_and_redo_name_their_step(store, make_header):
    header = make_header()
    undo, redo = (b for b in header.findChildren(QToolButton) if b.toolTip().startswith(("Undo", "Redo")))
    assert not undo.isEnabled()

    store.set_field(ELEMENT, "timeout", 9, "Timeout")
    assert undo.isEnabled() and undo.toolTip().startswith("Undo Timeout")

    undo.click()
    assert store.document.element.timeout is None
    assert redo.isEnabled() and redo.toolTip().startswith("Redo Timeout")


def test_resume_mode_is_chosen_and_remembered(store, theme, settings, make_header, qtbot):
    header = make_header()
    resume_actions(header)["After 5 s"].trigger()

    assert header.resume_mode is ResumeMode.AFTER_5_S
    assert "5 s" in buttons(header)

    again = Header(store, theme, settings, True)
    qtbot.addWidget(again)
    assert again.resume_mode is ResumeMode.AFTER_5_S


def test_resume_mode_is_now_from_the_cli(store, theme, settings, qtbot):
    settings.setValue("editor/resume", ResumeMode.AFTER_10_S.value)
    header = Header(store, theme, settings, False)
    qtbot.addWidget(header)

    assert header.resume_mode is ResumeMode.NOW


def test_stay_paused_hidden_without_the_pause_shortcut(monkeypatch, settings, make_header):
    monkeypatch.setattr(header_module, "_pause_available", lambda: False)
    settings.setValue("editor/resume", ResumeMode.PAUSED.value)

    header = make_header()

    assert header.resume_mode is ResumeMode.NOW
    assert not any(text.startswith("Stay paused") for text in resume_actions(header))


def test_theme_is_chosen_from_its_menu(theme, make_header):
    header = make_header()
    button = next(b for b in header.findChildren(QToolButton) if b.toolTip() == "Theme")

    next(action for action in button.menu().actions() if action.text() == "Dark").trigger()

    assert theme.choice is ThemeChoice.DARK


def test_name_is_centered_on_the_badges(make_store, make_header):
    header = make_header(on=make_store(timeout=9))
    name = next(label for label in header.findChildren(CenteredLabel) if label.text() == "button")
    (own,) = header.findChildren(Badge)
    image = QImage(header.size(), QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white)
    header.render(image)

    def center(widget) -> float:
        """Middle of the dark pixels of a widget, in header rows."""
        rows = [
            y
            for y in range(widget.y(), widget.y() + widget.height())
            if any(image.pixelColor(x, y).lightness() < 180 for x in range(widget.x(), widget.x() + widget.width()))
        ]
        return (rows[0] + rows[-1]) / 2

    assert abs(center(name) - center(own)) <= 0.5


def test_resume_menu_has_a_title_icons_and_a_check(make_header):
    header = make_header()
    menu = buttons(header)["Now"].menu()
    actions = resume_actions(header)

    (title,) = [action for action in menu.actions() if isinstance(action, QWidgetAction)]
    assert title.defaultWidget().text() == "Then resume the run"
    assert all(not action.icon().isNull() for action in actions.values())
    assert [action.text() for action in actions.values() if action.text().endswith(CHECK)] == [f"Now{CHECK}"]

    actions["After 3 s"].trigger()

    assert [action.text() for action in actions.values() if action.text().endswith(CHECK)] == [f"After 3 s{CHECK}"]
