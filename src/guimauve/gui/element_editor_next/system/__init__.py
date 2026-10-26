from guimauve.gui.element_editor_next.system.appearance import fallback_fonts, is_dark_scheme, watch_scheme
from guimauve.gui.element_editor_next.system.detect import Platform, current_platform
from guimauve.gui.element_editor_next.system.screens import (
    ScreenGeometry,
    ScreenMap,
    match_screens,
    to_logical,
    to_physical,
)
from guimauve.gui.element_editor_next.system.window import (
    is_excluded_from_capture,
    keep_on_top,
    out_of_capture,
    show_without_focus,
)
