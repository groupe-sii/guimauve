import numpy as np
import pytest

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state import Document, Store
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import ImageVariant, Target, TextVariant

SCREENS = [Screen(-1280, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(-1280, 0, 1280, 1024)]
CODE = {"mouse_speed": 500, "search_area": Area(left=0, top=0, right=1920, bottom=540)}


def image(name: str, *targets: str) -> ImageVariant:
    return ImageVariant(
        name=name,
        image=np.zeros((40, 120, 3), np.uint8),
        targets=[Target(name=target, x=10, y=20) for target in targets],
    )


@pytest.fixture
def make_store():
    """Store on an element with the given variants, code overrides and screens."""

    def make(variants=None, screens=SCREENS, code=CODE, **fields) -> Store:
        variants = [image("light", "icon", "arrow"), image("dark", "icon")] if variants is None else variants
        element = Element(name="button", variants=variants, **fields)
        return Store(Document(element, code), Parameters().default, screens)

    return make


@pytest.fixture
def store(make_store):
    return make_store()


@pytest.fixture
def text_variant():
    return TextVariant(name="label", text="Sign in")
