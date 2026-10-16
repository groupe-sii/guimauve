"""Qt stylesheet and palette generated from the tokens."""

from dataclasses import asdict
from string import Template

from PySide6.QtGui import QColor, QPalette

from guimauve.gui.element_editor_next.theme.color import mix
from guimauve.gui.element_editor_next.theme.tokens import METRICS, TYPE, Palette

WHITE = "#FFFFFF"
BLACK = "#000000"
SEGMENT_HEIGHT = METRICS.control_height - 4
"""Segment inside the track of a segmented control, which has 1 px of border and 1 px of margin on each side."""

_QSS = Template("""
QToolTip {
    color: $text;
    background: $surface_raised;
    border: 1px solid $border_strong;
    padding: ${space1}px ${space2}px;
}

QMenu {
    background: $surface;
    border: 1px solid $border;
    border-radius: ${radius_control}px;
    padding: ${space1}px;
}
QMenu::item {
    color: $text;
    padding: ${space1}px ${space3}px;
    border-radius: ${space1}px;
}
QMenu::item:selected { background: $accent_tint; }
QMenu::item:disabled { color: $text_muted; }
QMenu::separator { height: 1px; background: $border; margin: ${space1}px 0; }

QLineEdit, QAbstractSpinBox, QComboBox {
    min-height: ${inner_height}px;
    padding: 0 ${space2}px;
    color: $text;
    background: $surface;
    border: 1px solid $border;
    border-radius: ${radius_control}px;
    selection-background-color: $accent_fill;
    selection-color: $white;
}
QLineEdit:hover, QAbstractSpinBox:hover, QComboBox:hover { border-color: $border_strong; }
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus { border-color: $accent; }
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled { color: $text_muted; background: $surface_raised; }
QLineEdit[invalid="true"], QAbstractSpinBox[invalid="true"], QComboBox[invalid="true"] { border-color: $error; }

QPushButton {
    min-height: ${inner_height}px;
    padding: 0 ${space3}px;
    color: $text;
    background: $surface;
    border: 1px solid $border_strong;
    border-radius: ${radius_control}px;
    font-weight: $medium;
}
QPushButton:hover { background: $track; }
QPushButton:pressed { background: $border; }
QPushButton:focus { border-color: $accent; }
QPushButton:disabled { color: $text_muted; background: $surface; border-color: $border; }

QPushButton[variant="primary"] { color: $white; background: $accent_fill; border-color: $accent_fill; }
QPushButton[variant="primary"]:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton[variant="primary"]:pressed { background: $primary_pressed; border-color: $primary_pressed; }
QPushButton[variant="primary"]:focus { border-color: $text; }
QPushButton[variant="primary"]:disabled { color: $text_muted; background: $track; border-color: $track; }

QPushButton[variant="ghost"] { color: $text_secondary; background: transparent; border-color: transparent; }
QPushButton[variant="ghost"]:hover { background: $track; }
QPushButton[variant="ghost"]:pressed { background: $border; }
QPushButton[variant="ghost"]:focus { border-color: $accent; }
QPushButton[variant="ghost"]:disabled { color: $text_muted; background: transparent; }

QToolButton {
    padding: ${space1}px;
    color: $text_secondary;
    background: transparent;
    border: 1px solid transparent;
    border-radius: ${radius_control}px;
}
QToolButton:hover { background: $track; }
QToolButton:pressed { background: $border; }
QToolButton:checked { color: $accent; background: $accent_tint; }
QToolButton:focus { border-color: $accent; }

QFrame[segmented="true"] {
    background: $track;
    border: 1px solid transparent;
    border-radius: ${track_radius}px;
}
QFrame[segmented="true"]:focus { border-color: $accent; }
QPushButton[segment="true"] {
    min-height: ${segment_inner_height}px;
    padding: 0 ${space2}px;
    color: $text_secondary;
    background: transparent;
    border: 1px solid transparent;
    border-radius: ${segment_radius}px;
    font-size: ${small}px;
    font-weight: $medium;
}
QPushButton[segment="true"]:hover:!checked { color: $text; background: transparent; }
QPushButton[segment="true"]:checked { color: $text; background: $surface; border-color: $border_strong; }
QPushButton[segment="true"]:disabled { color: $text_muted; }

QLabel[badge="inherit"] {
    padding: 0 ${space2}px;
    color: $inherit;
    background: $inherit_tint;
    border-radius: ${badge_radius}px;
    font-size: ${caption}px;
    font-weight: $bold;
}

QFrame[section="true"] { border-bottom: 1px solid $border; }
QPushButton[sectionHeader="true"] {
    min-height: ${inner_height}px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: ${radius_control}px;
}
QPushButton[sectionHeader="true"]:hover { background: $track; }
QPushButton[sectionHeader="true"]:focus { border-color: $accent; }
QLabel[sectionTitle="true"] { color: $text; font-weight: $semibold; }
QLabel[muted="true"] { color: $text_muted; font-size: ${small}px; }

QFrame[banner="neutral"] { background: $surface_raised; border: 1px solid $border; }
QFrame[banner="inherit"] { background: $inherit_tint; }
QFrame[banner="warning"] { background: $warning_tint; }
QFrame[banner="error"] { background: $error_tint; }
QFrame[banner="neutral"], QFrame[banner="inherit"], QFrame[banner="warning"], QFrame[banner="error"] {
    border-radius: ${radius_control}px;
}
QFrame[strip="true"] { border: 0; border-bottom: 1px solid $border; border-radius: 0; }

QScrollBar:vertical { width: ${space2}px; background: transparent; margin: 0; }
QScrollBar:horizontal { height: ${space2}px; background: transparent; margin: 0; }
QScrollBar::handle { background: $border_strong; border-radius: ${space1}px; }
QScrollBar::handle:vertical { min-height: ${control_height}px; }
QScrollBar::handle:horizontal { min-width: ${control_height}px; }
QScrollBar::handle:hover { background: $text_muted; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
""")


def primary_hover(palette: Palette) -> str:
    """Primary button under the mouse: darker in both themes, so white text stays readable."""
    return mix(palette.accent_fill, BLACK, 0.1)


def primary_pressed(palette: Palette) -> str:
    return mix(palette.accent_fill, BLACK, 0.2)


def stylesheet(palette: Palette) -> str:
    """Stylesheet of the application; buttons take their look from the dynamic property "variant"."""
    return _QSS.substitute(
        asdict(palette),
        white=WHITE,
        primary_hover=primary_hover(palette),
        primary_pressed=primary_pressed(palette),
        control_height=METRICS.control_height,
        inner_height=METRICS.control_height - 2,  # min-height excludes the 1 px borders
        radius_control=METRICS.radius_control,
        space1=METRICS.space(1),
        space2=METRICS.space(2),
        space3=METRICS.space(3),
        track_radius=METRICS.pill(METRICS.control_height),
        segment_inner_height=SEGMENT_HEIGHT - 2,
        segment_radius=METRICS.pill(SEGMENT_HEIGHT),
        badge_radius=METRICS.pill(METRICS.badge_height),
        caption=TYPE.caption,
        small=TYPE.small,
        medium=TYPE.medium,
        semibold=TYPE.semibold,
        bold=TYPE.bold,
    )


def qpalette(palette: Palette) -> QPalette:
    """Qt palette for what the stylesheet does not cover, such as text selection and widgets drawn by Fusion."""
    result = QPalette()
    roles = {
        QPalette.ColorRole.Window: palette.background,
        QPalette.ColorRole.WindowText: palette.text,
        QPalette.ColorRole.Base: palette.surface,
        QPalette.ColorRole.AlternateBase: palette.surface_raised,
        QPalette.ColorRole.Text: palette.text,
        QPalette.ColorRole.PlaceholderText: palette.text_muted,
        QPalette.ColorRole.Button: palette.surface,
        QPalette.ColorRole.ButtonText: palette.text,
        QPalette.ColorRole.ToolTipBase: palette.surface_raised,
        QPalette.ColorRole.ToolTipText: palette.text,
        QPalette.ColorRole.Highlight: palette.accent_fill,
        QPalette.ColorRole.HighlightedText: WHITE,
        QPalette.ColorRole.Link: palette.accent,
        QPalette.ColorRole.Light: palette.surface,
        QPalette.ColorRole.Midlight: palette.border,
        QPalette.ColorRole.Mid: palette.border_strong,
        QPalette.ColorRole.Dark: palette.border_strong,
        QPalette.ColorRole.Shadow: palette.border_strong,
    }
    for role, color in roles.items():
        result.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        result.setColor(QPalette.ColorGroup.Disabled, role, QColor(palette.text_muted))
    return result
