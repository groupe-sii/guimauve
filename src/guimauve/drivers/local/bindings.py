from typing import Optional

from pynput.keyboard import Key as Key_
from pynput.keyboard import KeyCode
from pynput.mouse import Button as Mouse_

from guimauve.enums import Button, Key

KEY_MAP = {
    Key.ALT: Key_.alt_l,
    Key.ALT_R: Key_.alt_r,
    Key.ALT_GR: Key_.alt_gr,
    Key.BACKSPACE: Key_.backspace,
    Key.CAPS_LOCK: Key_.caps_lock,
    Key.CTRL: Key_.ctrl_l,
    Key.CTRL_R: Key_.ctrl_r,
    Key.DELETE: Key_.delete,
    Key.END: Key_.end,
    Key.ENTER: Key_.enter,
    Key.ESC: Key_.esc,
    Key.HOME: Key_.home,
    Key.INSERT: Key_.insert,
    Key.MEDIA_PLAY_PAUSE: Key_.media_play_pause,
    Key.MEDIA_NEXT: Key_.media_next,
    Key.MEDIA_PREVIOUS: Key_.media_previous,
    Key.MEDIA_VOLUME_MUTE: Key_.media_volume_mute,
    Key.MEDIA_VOLUME_DOWN: Key_.media_volume_down,
    Key.MEDIA_VOLUME_UP: Key_.media_volume_up,
    Key.META: Key_.cmd_l,
    Key.META_R: Key_.cmd_r,
    Key.NUM_LOCK: Key_.num_lock,
    Key.PAGE_UP: Key_.page_up,
    Key.PAGE_DOWN: Key_.page_down,
    Key.PAUSE: Key_.pause,
    Key.PRINT_SCREEN: Key_.print_screen,
    Key.SCROLL_LOCK: Key_.scroll_lock,
    Key.SHIFT: Key_.shift_l,
    Key.SHIFT_R: Key_.shift_r,
    Key.SPACE: Key_.space,
    Key.SUPER: Key_.cmd_l,
    Key.SUPER_R: Key_.cmd_r,
    Key.TAB: Key_.tab,
    Key.DOWN: Key_.down,
    Key.LEFT: Key_.left,
    Key.RIGHT: Key_.right,
    Key.UP: Key_.up,
    Key.KP_0: KeyCode.from_vk(96),
    Key.KP_1: KeyCode.from_vk(97),
    Key.KP_2: KeyCode.from_vk(98),
    Key.KP_3: KeyCode.from_vk(99),
    Key.KP_4: KeyCode.from_vk(100),
    Key.KP_5: KeyCode.from_vk(101),
    Key.KP_6: KeyCode.from_vk(102),
    Key.KP_7: KeyCode.from_vk(103),
    Key.KP_8: KeyCode.from_vk(104),
    Key.KP_9: KeyCode.from_vk(105),
    Key.KP_ADD: KeyCode.from_vk(107),
    Key.KP_DECIMAL: KeyCode.from_vk(110),
    Key.KP_DIVIDE: KeyCode.from_vk(111),
    Key.KP_ENTER: Key_.enter,
    Key.KP_MULTIPLY: KeyCode.from_vk(106),
    Key.KP_SUBTRACT: KeyCode.from_vk(109),
    Key.F1: Key_.f1,
    Key.F2: Key_.f2,
    Key.F3: Key_.f3,
    Key.F4: Key_.f4,
    Key.F5: Key_.f5,
    Key.F6: Key_.f6,
    Key.F7: Key_.f7,
    Key.F8: Key_.f8,
    Key.F9: Key_.f9,
    Key.F10: Key_.f10,
    Key.F11: Key_.f11,
    Key.F12: Key_.f12,
    Key.DIGIT_0: "0",
    Key.DIGIT_1: "1",
    Key.DIGIT_2: "2",
    Key.DIGIT_3: "3",
    Key.DIGIT_4: "4",
    Key.DIGIT_5: "5",
    Key.DIGIT_6: "6",
    Key.DIGIT_7: "7",
    Key.DIGIT_8: "8",
    Key.DIGIT_9: "9",
    Key.A_GRAVE: "à",
    Key.C_CEDILLA: "ç",
    Key.E_ACUTE: "é",
    Key.E_GRAVE: "è",
    Key.A: "a",
    Key.B: "b",
    Key.C: "c",
    Key.D: "d",
    Key.E: "e",
    Key.F: "f",
    Key.G: "g",
    Key.H: "h",
    Key.I: "i",
    Key.J: "j",
    Key.K: "k",
    Key.L: "l",
    Key.M: "m",
    Key.N: "n",
    Key.O: "o",
    Key.P: "p",
    Key.Q: "q",
    Key.R: "r",
    Key.S: "s",
    Key.T: "t",
    Key.U: "u",
    Key.V: "v",
    Key.W: "w",
    Key.X: "x",
    Key.Y: "y",
    Key.Z: "z",
    Key.AMPERSAND: "&",
    Key.ASTERISK: "*",
    Key.AT: "@",
    Key.BACKSLASH: "\\",
    Key.CARET: "^",
    Key.COLON: ":",
    Key.COMMA: ",",
    Key.DOLLAR: "$",
    Key.DOT: ".",
    Key.DOUBLE_QUOTE: '"',
    Key.EQUAL: "=",
    Key.EXCLAMATION: "!",
    Key.GRAVE: "`",
    Key.GREATER_THAN: ">",
    Key.HASH: "#",
    Key.LESS_THAN: "<",
    Key.MINUS: "-",
    Key.PERCENT: "%",
    Key.PIPE: "|",
    Key.PLUS: "+",
    Key.QUESTION: "?",
    Key.QUOTE: "'",
    Key.SEMICOLON: ";",
    Key.SLASH: "/",
    Key.TILDE: "~",
    Key.UNDERSCORE: "_",
    Key.LEFT_BRACE: "{",
    Key.LEFT_BRACKET: "[",
    Key.LEFT_PAREN: "(",
    Key.RIGHT_BRACE: "}",
    Key.RIGHT_BRACKET: "]",
    Key.RIGHT_PAREN: ")",
}

MOUSE_MAP = {
    Button.LEFT: Mouse_.left,
    Button.RIGHT: Mouse_.right,
    Button.MIDDLE: Mouse_.middle,
}

# ---------------------------------------------------------------------------
# Reverse map: pynput -> Key (local capture only)
# ---------------------------------------------------------------------------

_SPECIAL_REVERSE: dict = {}
_VK_REVERSE: dict = {}
_CHAR_REVERSE: dict = {}

# Several Key map to the same pynput value: pick the canonical one.
_REVERSE_WINNERS = {
    Key_.enter: Key.ENTER,  # not KP_ENTER
    Key_.cmd_l: Key.META,  # not SUPER
    Key_.cmd_r: Key.META_R,  # not SUPER_R
}

for _key, _val in KEY_MAP.items():
    if isinstance(_val, str):
        _CHAR_REVERSE.setdefault(_val, _key)
    elif isinstance(_val, KeyCode) and _val.vk is not None:
        _VK_REVERSE.setdefault(_val.vk, _key)
    else:  # Key_ special key
        _SPECIAL_REVERSE.setdefault(_val, _key)

_SPECIAL_REVERSE.update(_REVERSE_WINNERS)  # override arbitrary winners


def key_from_pynput(key) -> Optional[Key]:
    """Map a pynput event (Key_ or KeyCode) back to a Key."""
    if isinstance(key, Key_):
        return _SPECIAL_REVERSE.get(key)
    if isinstance(key, KeyCode):
        # vk BEFORE char: the keypad may report a .char under NumLock;
        # checking vk first prevents capturing KP_0 as DIGIT_0.
        if key.vk is not None and key.vk in _VK_REVERSE:
            return _VK_REVERSE[key.vk]
        if key.char is not None:
            return _CHAR_REVERSE.get(key.char) or _CHAR_REVERSE.get(key.char.lower())
    return None


# ---------------------------------------------------------------------------
# Reverse map: pynput -> Button (local capture only)
# ---------------------------------------------------------------------------

_BUTTON_REVERSE = {_v: _k for _k, _v in MOUSE_MAP.items()}


def button_from_pynput(button) -> Optional[Button]:
    """Map a pynput mouse button back to a Button."""
    return _BUTTON_REVERSE.get(button)
