"""Design tokens of the editor: colors, sizes and type, for both themes.

Plain values without Qt, shared by the generated stylesheet and the widgets that paint themselves.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Interface colors of one theme, as #RRGGBB.

    Rose (accent) is for actions and selection, violet (inherit) for inheritance and overrides. Each has a text
    color, a fill for solid backgrounds under white text, and a tint for light backgrounds under the text color.
    """

    background: str
    surface: str
    surface_raised: str
    border: str
    border_strong: str
    text: str
    text_secondary: str
    text_muted: str

    accent: str
    accent_fill: str
    accent_tint: str
    inherit: str
    inherit_fill: str
    inherit_tint: str

    track: str
    """Background of a segmented control."""
    switch_track: str
    """Background of a switch that is off."""


LIGHT = Palette(
    background="#F5F4F8",
    surface="#FFFFFF",
    surface_raised="#F8F7FB",
    border="#E4E2EA",
    border_strong="#D3D0DC",
    text="#1E1B26",
    text_secondary="#4B4757",
    text_muted="#6B6678",
    accent="#A63A72",
    accent_fill="#A63A72",
    accent_tint="#F3DCE8",
    inherit="#6E4BB3",
    inherit_fill="#6E4BB3",
    inherit_tint="#EEE8F8",
    track="#EFEDF3",
    switch_track="#CFCAD8",
)

DARK = Palette(
    background="#17151C",
    surface="#211E27",
    surface_raised="#2A2631",
    border="#36323F",
    border_strong="#45404F",
    text="#ECEAF1",
    text_secondary="#C5C1CF",
    text_muted="#9A95A6",
    accent="#E58BB8",
    accent_fill="#B5487F",
    accent_tint="#4A2B3E",
    inherit="#B39DEB",
    inherit_fill="#7C5BC4",
    inherit_tint="#2F2742",
    track="#2A2631",
    switch_track="#45404F",
)


@dataclass(frozen=True)
class Semantic:
    """Colors with a fixed meaning, the same in both themes."""

    target: str = "#1F5FBF"
    area: str = "#C2620C"
    """Match area and other zones drawn on an image."""
    success: str = "#1E7F4E"
    warning: str = "#B5590E"
    error: str = "#B42318"


SEMANTIC = Semantic()


@dataclass(frozen=True)
class Brand:
    """Colors of the logo, the application icon and the spinner; never used for interface controls."""

    rose: str = "#D8679F"
    violet: str = "#9A7DE0"
    overlap: str = "#7350B3"


BRAND = Brand()


@dataclass(frozen=True)
class Metrics:
    """Sizes in logical pixels; Qt scales them with the screen."""

    control_height: int = 28
    grid: int = 4
    radius_control: int = 8
    radius_panel: int = 12
    radius_card: int = 16
    icon: int = 16
    switch_width: int = 32
    switch_height: int = 18
    badge_height: int = 16
    dot: int = 6
    """Violet dot of an overridden value."""

    def space(self, steps: int) -> int:
        """Spacing on the grid: space(2) is 8 px."""
        return self.grid * steps

    @staticmethod
    def pill(height: int) -> int:
        """Radius that rounds both ends of an element of this height, e.g. a badge or a segmented control."""
        return height // 2


METRICS = Metrics()


@dataclass(frozen=True)
class Typography:
    """Font family, sizes in pixels and weights; fallback fonts come from the system layer."""

    family: str = "Manrope"

    caption: int = 11
    small: int = 12
    body: int = 13
    title: int = 14

    regular: int = 400
    medium: int = 500
    semibold: int = 600
    bold: int = 700


TYPE = Typography()
