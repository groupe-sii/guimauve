"""Element editor; the contract can be imported without loading Qt."""

import logging

from guimauve.gui.element_editor.contract import Context, EditorResult, ResumeMode
from guimauve.log import fields

logger = logging.getLogger(__name__)


def start_element_editor(context: Context) -> EditorResult:
    """Opens the editor and returns once it is closed: the element to save, or None, and the resume mode.

    The caller saves the element; the editor never writes anything.
    """
    from guimauve.gui.element_editor.app import run  # loads Qt only when the editor opens

    # At DEBUG: the caller, the controller or the CLI, tells at INFO why the editor opens and what came out of it
    name = context.element.name
    logger.debug("Element editor opened for %s", name, extra=fields(element=name, action=context.action or None))
    result = run(context)
    logger.debug(
        "Element editor closed for %s: %s",
        name,
        "saved" if result.element is not None else "nothing to save",
        extra=fields(element=name, saved=result.element is not None, resume=result.resume.value),
    )
    return result


__all__ = ["Context", "EditorResult", "ResumeMode", "start_element_editor"]
