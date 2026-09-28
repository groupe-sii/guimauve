import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from guimauve.detection.ocr import Ocr
from guimauve.enums import OcrFidelity


def _font(size):
    return ImageFont.load_default(size=size)


@pytest.fixture
def render_lines():
    def render(lines, font_size=26, padding=12, line_gap=8, bg=(245, 245, 245), fg=(15, 15, 15)):
        """Render one or more lines of text on a tightly-cropped canvas. Returns a BGR np.ndarray."""
        font = _font(font_size)
        dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        sizes = [dummy.textbbox((0, 0), line, font=font)[2:] for line in lines]

        width = max(w for w, h in sizes) + padding * 2
        line_height = max(h for w, h in sizes)
        height = line_height * len(lines) + line_gap * (len(lines) - 1) + padding * 2

        image = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(image)
        y = padding
        for line in lines:
            draw.text((padding, y), line, font=font, fill=fg)
            y += line_height + line_gap

        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    return render


@pytest.fixture
def blank_haystack():
    def blank(width=800, height=600, bg=(250, 250, 250)):
        return np.full((height, width, 3), bg, dtype=np.uint8)

    return blank


@pytest.fixture
def paste():
    def paste_(haystack, patch, x, y):
        h, w = patch.shape[:2]
        haystack[y : y + h, x : x + w] = patch
        return haystack

    return paste_


@pytest.fixture
def params():
    def params_(**overrides):
        base = {"fidelity": OcrFidelity.FAST, "confidence_threshold": 0.8}
        base.update(overrides)
        return base

    return params_


@pytest.fixture(scope="module")
def ocr():
    return Ocr()
