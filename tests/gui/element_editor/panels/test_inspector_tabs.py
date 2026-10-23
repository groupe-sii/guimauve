import pytest
from PySide6.QtWidgets import QPushButton

from guimauve.gui.element_editor_next.panels import Inspector, InspectorPanel, VariantInspector
from guimauve.gui.element_editor_next.panels.inspector_panel import ELEMENT_TAB, VARIANT_TAB


@pytest.fixture
def show(theme, qtbot):
    def make(store) -> InspectorPanel:
        panel = InspectorPanel(store, theme)
        qtbot.addWidget(panel)
        panel.resize(400, 700)
        panel.show()
        return panel

    return make


def tab(panel, text: str) -> QPushButton:
    return next(b for b in panel.findChildren(QPushButton) if b.property("tab") and b.text().startswith(text))


def test_element_tab_first(store, show):
    panel = show(store)

    assert panel.tab() == ELEMENT_TAB
    assert panel.findChild(Inspector).isVisible()


def test_variant_tab_shows_the_selection(store, show):
    panel = show(store)

    tab(panel, "Variant").click()

    assert panel.tab() == VARIANT_TAB
    assert panel.findChild(VariantInspector).isVisible()
    assert tab(panel, "Variant").text() == "Variant"
    store.select(store.variant_keys()[1])
    assert panel.tab() == VARIANT_TAB


def test_selection_does_not_change_the_tab(store, show):
    panel = show(store)

    store.select(store.variant_keys()[1])

    assert panel.tab() == ELEMENT_TAB


def test_variant_tab_disabled_without_variant(make_store, show):
    store = make_store([], x=1)
    panel = show(store)

    assert not tab(panel, "Variant").isEnabled()


def test_back_to_element_when_the_last_variant_goes(make_store, show, text_variant):
    store = make_store([text_variant], x=1)
    panel = show(store)
    panel.set_tab(VARIANT_TAB)

    store.remove_variant(store.variant_keys()[0])

    assert panel.tab() == ELEMENT_TAB
    assert not tab(panel, "Variant").isEnabled()
