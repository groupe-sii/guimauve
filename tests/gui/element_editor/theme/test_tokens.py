import re
from dataclasses import astuple

import pytest

from guimauve.gui.element_editor_next.theme import BRAND, DARK, LIGHT, METRICS, SEMANTIC, Palette

PALETTES = pytest.mark.parametrize("palette", [LIGHT, DARK], ids=["light", "dark"])


def luminance(color: str) -> float:
    """Relative luminance, as defined by WCAG 2."""
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("colors", [LIGHT, DARK, SEMANTIC, BRAND], ids=["light", "dark", "semantic", "brand"])
def test_colors_are_hex(colors):
    assert all(re.fullmatch(r"#[0-9A-F]{6}", color) for color in astuple(colors))


@PALETTES
@pytest.mark.parametrize("text", ["text", "text_secondary", "text_muted", "accent", "inherit"])
@pytest.mark.parametrize("surface", ["background", "surface", "surface_raised"])
def test_text_is_readable(palette: Palette, text: str, surface: str):
    assert contrast(getattr(palette, text), getattr(palette, surface)) >= 4.5


@PALETTES
@pytest.mark.parametrize("fill", ["accent_fill", "inherit_fill"])
def test_white_text_is_readable_on_fills(palette: Palette, fill: str):
    assert contrast("#FFFFFF", getattr(palette, fill)) >= 4.5


@PALETTES
@pytest.mark.parametrize(("text", "tint"), [("accent", "accent_tint"), ("inherit", "inherit_tint")])
def test_colored_text_is_readable_on_its_tint(palette: Palette, text: str, tint: str):
    assert contrast(getattr(palette, text), getattr(palette, tint)) >= 4.5


def test_spacing_follows_the_grid():
    assert [METRICS.space(n) for n in (1, 2, 3)] == [4, 8, 12]


def test_pill_rounds_both_ends():
    assert METRICS.pill(METRICS.control_height) == 14
