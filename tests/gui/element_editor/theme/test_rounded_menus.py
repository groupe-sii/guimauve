from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from guimauve.gui.element_editor_next.theme.menus import RoundedMenus, round_corners


def is_rounded(menu: QMenu) -> bool:
    """Transparent and frameless: what the corners need. The shadow flag is not checked, Windows drops it."""
    return menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) and bool(
        menu.windowFlags() & Qt.WindowType.FramelessWindowHint
    )


def test_round_corners(qtbot):
    menu = QMenu()
    qtbot.addWidget(menu)

    round_corners(menu)

    assert is_rounded(menu)


def test_every_menu_is_rounded_once_the_theme_applies(qapp, qtbot):
    menus = RoundedMenus()
    qapp.installEventFilter(menus)
    try:
        menu = QMenu()
        qtbot.addWidget(menu)
        menu.addAction("Item")
        menu.ensurePolished()
    finally:
        qapp.removeEventFilter(menus)

    assert is_rounded(menu)


def test_menu_made_translucent_by_its_style_is_rounded_too(qtbot):
    menu = QMenu()
    qtbot.addWidget(menu)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # as the windows11 style does

    round_corners(menu)

    assert is_rounded(menu)
