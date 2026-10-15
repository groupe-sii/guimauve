"""Undo and redo stacks of the session."""

from guimauve.gui.element_editor_next.state.commands import Command
from guimauve.gui.element_editor_next.state.document import Document


class History:
    """Runs commands on the document and keeps them for undo and redo, without limit for the session."""

    def __init__(self, document: Document):
        self._document = document
        self._undo: list[Command] = []
        self._redo: list[Command] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None

    def push(self, command: Command) -> None:
        """Runs a command; it merges into the previous one when both belong to the same gesture."""
        command.do(self._document)
        self._redo.clear()
        if self._undo and self._undo[-1].merge(command):
            return
        self._undo.append(command)

    def undo(self) -> Command | None:
        """Undoes the last command and returns it, or returns None when there is nothing to undo."""
        if not self._undo:
            return None
        command = self._undo.pop()
        command.undo(self._document)
        self._redo.append(command)
        return command

    def redo(self) -> Command | None:
        """Redoes the last undone command and returns it, or returns None when there is nothing to redo."""
        if not self._redo:
            return None
        command = self._redo.pop()
        command.do(self._document)
        self._undo.append(command)
        return command
