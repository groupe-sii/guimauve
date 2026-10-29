"""Menu of the sources of a capture, shared by the capture of an image and the capture of the Test."""

from collections.abc import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from guimauve.gui.element_editor_next.components import CHECK, add_item, add_title, follow_theme, styled_menu
from guimauve.gui.element_editor_next.services import CaptureSource
from guimauve.gui.element_editor_next.theme import Icon, ThemeManager

CAPTURE_DELAYS = (1, 3, 5, 10)


def fill_source_menu(
    menu: QMenu,
    theme: ThemeManager,
    title: str,
    delay: int,
    initial_error: str | None,
    chosen: Callable[[CaptureSource], None],
    delay_chosen: Callable[[int], None],
    custom_delay: Callable[[], None],
) -> None:
    """Fills a menu with the sources of a capture: Initial screen, Instant, After a delay and its delays, a file.

    :param delay: Delay kept, ticked in the submenu and given beside After a delay.
    :param initial_error: Why Initial screen is disabled, the screens not captured at opening.
    :param chosen: Called with the source chosen; DELAYED with the delay kept.
    :param delay_chosen: Called with another delay chosen, in seconds.
    :param custom_delay: Called when Custom… asks for a delay.
    """
    menu.clear()
    add_title(menu, title)
    initial = add_item(menu, "Initial screen\tat opening", Icon.MONITOR, theme, enabled=initial_error is None)
    initial.setToolTip(initial_error or "")
    initial.triggered.connect(lambda: chosen(CaptureSource.INITIAL))
    instant = add_item(menu, "Instant\tnow", Icon.CAMERA, theme)
    instant.triggered.connect(lambda: chosen(CaptureSource.INSTANT))
    delays = styled_menu(menu)
    for seconds in CAPTURE_DELAYS:
        action = QAction(f"{seconds} s" + (CHECK if seconds == delay else ""), delays)
        action.triggered.connect(lambda _=False, seconds=seconds: delay_chosen(seconds))
        delays.addAction(action)
    custom = QAction("Custom…" + (CHECK if delay not in CAPTURE_DELAYS else ""), delays)
    custom.triggered.connect(custom_delay)
    delays.addAction(custom)
    later = _add_submenu(menu, delays, f"After a delay\t{delay} s", Icon.TIMER, theme)
    later.setObjectName("captureLater")
    menu.addSeparator()
    file = add_item(menu, "Import a file…", Icon.IMAGE_UP, theme)
    file.triggered.connect(lambda: chosen(CaptureSource.FILE))


def _add_submenu(menu: QMenu, submenu: QMenu, text: str, name: Icon, theme: ThemeManager) -> QAction:
    action = menu.addMenu(submenu)
    action.setText(text)
    follow_theme(action, name, theme)
    return action
