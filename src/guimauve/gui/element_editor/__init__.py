"""Element editor; the contract can be imported without loading Qt."""

from guimauve.gui.element_editor.contract import Context, EditorResult, ResumeMode


def start_element_editor(context: Context) -> EditorResult:
    """Opens the editor and returns once it is closed: the element to save, or None, and the resume mode.

    The caller saves the element; the editor never writes anything.
    """
    from guimauve.gui.element_editor.app import run  # loads Qt only when the editor opens

    return run(context)


__all__ = ["Context", "EditorResult", "ResumeMode", "start_element_editor"]
