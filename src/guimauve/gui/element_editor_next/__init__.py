"""New element editor; the contract can be imported without loading Qt."""

import os

from guimauve.gui.element_editor_next.contract import Context, EditorResult, ResumeMode


def next_editor_enabled() -> bool:
    """The new editor replaces the old one when GUIMAUVE_EDITOR is "next"; temporary, until the switch."""
    return os.environ.get("GUIMAUVE_EDITOR") == "next"


def start_element_editor(context: Context) -> EditorResult:
    """Opens the editor and returns once it is closed: the element to save, or None, and the resume mode.

    The caller saves the element; the editor never writes anything.
    """
    from guimauve.gui.element_editor_next.app import run  # loads Qt only when the editor opens

    return run(context)


__all__ = ["Context", "EditorResult", "ResumeMode", "next_editor_enabled", "start_element_editor"]
