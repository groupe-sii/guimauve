import pytest
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.panels.trial_banner import TrialBanner
from guimauve.gui.element_editor_next.state import ELEMENT, Mode


@pytest.fixture
def banner(store, qtbot):
    parent = QWidget()  # shown, and the banner with it unless it hides itself
    qtbot.addWidget(parent)
    widget = TrialBanner(store, parent)
    parent.show()
    yield widget  # the parent lives as long as the test


def test_hidden_in_edit_mode_without_trials(banner):
    assert not banner.isVisible()


def test_test_mode_counts_the_trials(store, banner):
    store.set_mode(Mode.TEST)
    assert banner.isVisible() and banner.text.full_text() == "Test mode · no trial value"
    assert not banner.apply.isEnabled() and not banner.discard.isEnabled()

    store.set_field(ELEMENT, "timeout", 9)
    store.set_field(store.variant_keys()[0], "match_index", 1)

    assert banner.text.full_text() == "Test mode · 2 trial values"
    assert banner.apply.isEnabled() and banner.discard.isEnabled()


def test_apply_writes_the_trials_into_the_element(store, banner):
    store.set_mode(Mode.TEST)
    store.set_field(ELEMENT, "timeout", 9)

    banner.apply.click()

    assert store.document.element.timeout == 9 and not store.has_trials


def test_discard_forgets_the_trials(store, banner):
    store.set_mode(Mode.TEST)
    store.set_field(ELEMENT, "timeout", 9)

    banner.discard.click()

    assert store.document.element.timeout is None and not store.has_trials


def test_edit_mode_tells_the_trials_are_kept(store, banner):
    store.set_mode(Mode.TEST)
    store.set_field(ELEMENT, "timeout", 9)

    store.set_mode(Mode.EDIT)

    assert banner.isVisible() and banner.text.full_text() == "1 trial value kept for the Test"
    assert not banner.apply.isVisible() and not banner.discard.isVisible()
