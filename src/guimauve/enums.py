from enum import Enum, auto

from guimauve.models.area import Area


class Key(Enum):
    # Controls
    ALT = auto()
    ALT_R = auto()
    BACKSPACE = auto()
    CAPS_LOCK = auto()
    CTRL = auto()
    CTRL_R = auto()
    DELETE = auto()
    END = auto()
    ENTER = auto()
    ESC = auto()
    HOME = auto()
    INSERT = auto()
    MEDIA_PLAY_PAUSE = auto()
    MEDIA_NEXT = auto()
    MEDIA_PREVIOUS = auto()
    MEDIA_VOLUME_MUTE = auto()
    MEDIA_VOLUME_DOWN = auto()
    MEDIA_VOLUME_UP = auto()
    META = auto()
    META_R = auto()
    NUM_LOCK = auto()
    PAGE_DOWN = auto()
    PAGE_UP = auto()
    PAUSE = auto()
    PRINT_SCREEN = auto()
    SCROLL_LOCK = auto()
    SHIFT = auto()
    SHIFT_R = auto()
    SPACE = auto()
    SUPER = auto()
    SUPER_R = auto()
    TAB = auto()

    # Arrows
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    UP = auto()

    # Keypad
    KP_0 = auto()
    KP_1 = auto()
    KP_2 = auto()
    KP_3 = auto()
    KP_4 = auto()
    KP_5 = auto()
    KP_6 = auto()
    KP_7 = auto()
    KP_8 = auto()
    KP_9 = auto()
    KP_ENTER = auto()

    # Function keys
    F1 = auto()
    F2 = auto()
    F3 = auto()
    F4 = auto()
    F5 = auto()
    F6 = auto()
    F7 = auto()
    F8 = auto()
    F9 = auto()
    F10 = auto()
    F11 = auto()
    F12 = auto()

    # Letters
    A = auto()
    B = auto()
    C = auto()
    D = auto()
    E = auto()
    F = auto()
    G = auto()
    H = auto()
    I = auto()
    J = auto()
    K = auto()
    L = auto()
    M = auto()
    N = auto()
    O = auto()
    P = auto()
    Q = auto()
    R = auto()
    S = auto()
    T = auto()
    U = auto()
    V = auto()
    W = auto()
    X = auto()
    Y = auto()
    Z = auto()

    # Punctuation and symbols
    BACKSLASH = auto()
    COLON = auto()
    COMMA = auto()
    DOT = auto()
    DOUBLE_QUOTE = auto()
    EQUAL = auto()
    MINUS = auto()
    PLUS = auto()
    QUOTE = auto()
    SEMICOLON = auto()
    SLASH = auto()
    UNDERSCORE = auto()


class Menu(Enum):
    HORIZONTAL = 0
    VERTICAL = 1


class Button(Enum):
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


class MouseDirection(Enum):
    STRAIGHT = auto()
    XY_X = auto()
    XY_Y = auto()


class MatchSort(Enum):
    CONFIDENCE = auto()
    XY_POSITION = auto()


class ScreenArea(Enum):
    FULL = (0, 0, 1, 1)
    LEFT = (0, 0, 0.5, 1)
    TOP = (0, 0, 1, 0.5)
    RIGHT = (0.5, 0, 1, 1)
    BOTTOM = (0, 0.5, 1, 1)

    TOP_LEFT = (0, 0, 0.5, 0.5)
    TOP_RIGHT = (0.5, 0, 1, 0.5)
    BOTTOM_RIGHT = (0.5, 0.5, 1, 1)
    BOTTOM_LEFT = (0, 0.5, 0.5, 1)

    COL_1 = (0, 0, 1 / 3, 1)
    COL_2 = (1 / 3, 0, 2 / 3, 1)
    COL_3 = (2 / 3, 0, 1, 1)

    ROW_1 = (0, 0, 1, 1 / 3)
    ROW_2 = (0, 1 / 3, 1, 2 / 3)
    ROW_3 = (0, 2 / 3, 1, 1)

    def get_area(self, screen_size) -> Area:
        w, h = screen_size
        l, t, r, b = self.value
        return Area(left=int(w * l), top=int(h * t), right=int(w * r), bottom=int(h * b))
