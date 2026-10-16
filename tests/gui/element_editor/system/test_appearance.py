import sys

import pytest

from guimauve.gui.element_editor_next.system import fallback_fonts, is_dark_scheme, windows


@pytest.mark.parametrize(("system", "first"), [("win32", "Segoe UI"), ("linux", "Noto Sans")])
def test_fallback_fonts(monkeypatch, system, first):
    monkeypatch.setattr(sys, "platform", system)
    assert fallback_fonts()[0] == first


def test_scheme_is_known(qapp):
    assert isinstance(is_dark_scheme(), bool)


@pytest.mark.skipif(sys.platform == "win32", reason="exclusion only fails outside Windows")
def test_win32_exclusion_fails_elsewhere():
    assert not windows.exclude_from_capture(0)
