from PySide6.QtGui import QFont, QFontInfo

from guimauve.gui.element_editor_next.theme import TYPE
from guimauve.gui.element_editor_next.theme.fonts import load_fonts


def test_manrope_is_available(qapp):
    assert load_fonts()
    assert QFontInfo(QFont(TYPE.family)).family() == TYPE.family


def test_every_weight_is_available(qapp):
    load_fonts()
    for weight in (TYPE.regular, TYPE.medium, TYPE.semibold, TYPE.bold):
        font = QFont(TYPE.family)
        font.setWeight(QFont.Weight(weight))
        assert QFontInfo(font).weight() == weight
