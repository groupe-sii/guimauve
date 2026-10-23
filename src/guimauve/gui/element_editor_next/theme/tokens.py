"""Design tokens of the editor: colors, sizes and type, for both themes.

Plain values without Qt, shared by the generated stylesheet and the widgets that paint themselves.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Interface colors of one theme, as #RRGGBB.

    Rose (accent) is for actions and selection, violet (inherit) for inheritance and overrides. Each has a text
    color, a fill for solid backgrounds under white text, and a tint for light backgrounds under the text color.
    Error, warning and success are for text, icons and borders, each with its tint; shapes drawn on images use
    SEMANTIC instead.
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

    error: str
    error_tint: str
    warning: str
    warning_tint: str
    success: str
    success_tint: str

    track: str
    """Background of a segmented control."""
    switch_track: str
    """Background of a switch that is off."""
    canvas: str
    canvas_dot: str
    """Background of the canvas and the dots of its grid."""


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
    error="#B42318",
    error_tint="#FDECEA",
    warning="#A3500D",
    warning_tint="#FDF1E6",
    success="#1E7F4E",
    success_tint="#EDF5F1",
    track="#EFEDF3",
    switch_track="#CFCAD8",
    canvas="#ECEAF0",
    canvas_dot="#D6D2DE",
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
    error="#D68680",
    error_tint="#3E1F24",
    warning="#D6A47A",
    warning_tint="#3F2A22",
    success="#83B99E",
    success_tint="#20312F",
    track="#2A2631",
    switch_track="#45404F",
    canvas="#141218",
    canvas_dot="#2C2833",
)


@dataclass(frozen=True)
class Semantic:
    """Colors with a fixed meaning, the same in both themes, for shapes drawn on images.

    Text and icons use the error, warning and success roles of the palette, readable in both themes.
    """

    target: str = "#1F5FBF"
    area: str = "#C2620C"
    """Match area and other zones drawn on an image."""
    image_border: str = "#B9B5C3"
    """Line around the image on the canvas, in both themes since it frames the capture."""
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
    label_width: int = 112
    label_ratio: float = 0.4
    """Column of the labels in the inspector, as a share of the width of a field; never below label_width."""
    variants_width: int = 240
    variants_min_width: int = 200
    variants_max_width: int = 400
    inspector_width: int = 400
    inspector_min_width: int = 380
    inspector_max_width: int = 560
    """Column of the labels in the inspector."""
    number_width: int = 64
    """Number box next to a slider."""
    variants_collapsed_width: int = 64
    thumbnail_width: int = 52
    thumbnail_height: int = 34
    thumbnail_small_width: int = 42
    thumbnail_small_height: int = 28
    """Frames of the thumbnails in the variant list, expanded then collapsed; the image fits inside the padding."""
    status_dot: int = 8
    """Dot summing up a collapsed variant: errors, warnings, then overrides."""
    canvas_bar_height: int = 44
    canvas_status_height: int = 26
    canvas_grid: int = 16
    """Spacing of the dots behind the image."""
    canvas_margin: int = 24
    """Space kept around the image when it fits the canvas."""

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
