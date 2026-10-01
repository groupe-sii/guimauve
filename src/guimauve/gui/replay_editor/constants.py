"""Shared constants for the replay editor.

Anything used by more than one widget or preview module lives here, so
adding a new key or tweaking a color happens in a single place.
"""

from PySide6.QtGui import QColor

EVENT_COLORS: dict[str, QColor] = {
    "key_down": QColor("#378ADD"),
    "key_up": QColor("#378ADD"),
    "mouse_down": QColor("#D85A30"),
    "mouse_up": QColor("#D85A30"),
    "mouse_scroll": QColor("#EF9F27"),
}

HIDDEN_EVENT_ACTIONS: set[str] = {"mouse_move"}

BUTTON_COLORS: dict[str, QColor] = {
    "LEFT": QColor("#378ADD"),
    "RIGHT": QColor("#D85A30"),
    "MIDDLE": QColor("#639922"),
}

SCROLL_BATCH_GAP: float = 0.2
SCROLL_FADE: float = 0.4

RIPPLE_LIFETIME: float = 0.5
RIPPLE_MAX_RADIUS: float = 30.0
RIPPLE_MAX_RADIUS_DOUBLE: float = 50.0

DOUBLE_CLICK_MAX_INTERVAL: float = 0.5
DOUBLE_CLICK_MAX_DISTANCE: float = 20.0

KEYBOARD_LINGER: float = 1.5
KEYBOARD_FADE: float = 3.0
MAX_TYPED_KEYS: int = 25

MODIFIERS: set[str] = {
    "CTRL",
    "CTRL_R",
    "SHIFT",
    "SHIFT_R",
    "ALT",
    "ALT_R",
    "ALT_GR",
    "META",
    "META_R",
    "SUPER",
    "SUPER_R",
}


SHORTCUT_MODIFIERS: set[str] = {
    "CTRL",
    "CTRL_R",
    "ALT",
    "ALT_R",
    "ALT_GR",
    "META",
    "META_R",
    "SUPER",
    "SUPER_R",
}

KEY_DISPLAY: dict[str, str] = {
    "SPACE": "␣",
    "ENTER": "⏎",
    "TAB": "⇥",
    "BACKSPACE": "⌫",
    "DELETE": "⌦",
    "ESC": "Esc",
    "SHIFT": "Shift",
    "SHIFT_R": "Shift",
    "CTRL": "Ctrl",
    "CTRL_R": "Ctrl",
    "ALT": "Alt",
    "ALT_R": "Alt",
    "ALT_GR": "AltGr",
    "META": "⌘",
    "META_R": "⌘",
    "SUPER": "⌘",
    "SUPER_R": "⌘",
    "UP": "↑",
    "DOWN": "↓",
    "LEFT": "←",
    "RIGHT": "→",
    "HOME": "Home",
    "END": "End",
    "PAGE_UP": "PgUp",
    "PAGE_DOWN": "PgDn",
    "INSERT": "Ins",
    "CAPS_LOCK": "Caps",
    "DIGIT_0": "0",
    "DIGIT_1": "1",
    "DIGIT_2": "2",
    "DIGIT_3": "3",
    "DIGIT_4": "4",
    "DIGIT_5": "5",
    "DIGIT_6": "6",
    "DIGIT_7": "7",
    "DIGIT_8": "8",
    "DIGIT_9": "9",
    "AMPERSAND": "&",
    "ASTERISK": "*",
    "AT": "@",
    "BACKSLASH": "\\",
    "CARET": "^",
    "COLON": ":",
    "COMMA": ",",
    "DOLLAR": "$",
    "DOT": ".",
    "DOUBLE_QUOTE": '"',
    "EQUAL": "=",
    "EXCLAMATION": "!",
    "GRAVE": "`",
    "GREATER_THAN": ">",
    "HASH": "#",
    "LESS_THAN": "<",
    "MINUS": "-",
    "PERCENT": "%",
    "PIPE": "|",
    "PLUS": "+",
    "QUESTION": "?",
    "QUOTE": "'",
    "SEMICOLON": ";",
    "SLASH": "/",
    "TILDE": "~",
    "UNDERSCORE": "_",
    "LEFT_PAREN": "(",
    "RIGHT_PAREN": ")",
    "LEFT_BRACKET": "[",
    "RIGHT_BRACKET": "]",
    "LEFT_BRACE": "{",
    "RIGHT_BRACE": "}",
    "E_ACUTE": "é",
    "E_GRAVE": "è",
    "C_CEDILLA": "ç",
    "A_GRAVE": "à",
    "KP_0": "0",
    "KP_1": "1",
    "KP_2": "2",
    "KP_3": "3",
    "KP_4": "4",
    "KP_5": "5",
    "KP_6": "6",
    "KP_7": "7",
    "KP_8": "8",
    "KP_9": "9",
    "KP_ADD": "+",
    "KP_SUBTRACT": "-",
    "KP_MULTIPLY": "*",
    "KP_DIVIDE": "/",
    "KP_DECIMAL": ".",
    "KP_ENTER": "⏎",
}
