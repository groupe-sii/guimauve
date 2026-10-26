from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from guimauve.gui.element_editor_next.components import add_item, follow_theme, styled_menu
from guimauve.gui.element_editor_next.theme import Icon, ThemeChoice


def test_item_icon_follows_the_theme(theme, qtbot):
    menu = styled_menu()
    qtbot.addWidget(menu)
    item = add_item(menu, "Instant", Icon.CAMERA, theme)
    before = item.icon().cacheKey()

    theme.set_choice(ThemeChoice.DARK if not theme.is_dark else ThemeChoice.LIGHT)

    assert item.icon().cacheKey() != before


def test_items_of_a_rebuilt_menu_leave_the_theme(theme, qtbot):
    menu = styled_menu()
    qtbot.addWidget(menu)
    add_item(menu, "Instant", Icon.CAMERA, theme)
    submenu = QMenu(menu)
    follow_theme(menu.addMenu(submenu), Icon.TIMER, theme)

    menu.clear()  # deletes its items

    theme.changed.emit()  # no item left to repaint, and no error


def test_follow_theme_sets_the_icon(theme, qtbot):
    action = QAction("Later")

    follow_theme(action, Icon.TIMER, theme)

    assert not action.icon().isNull()
