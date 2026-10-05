"""Top toolbar: Record / Replay / Open / Set background / Save.

This widget only builds the actions and lays them out — it does not
know what clicking them should do. The main window connects each
action's ``triggered`` signal to its own logic.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QSizePolicy, QToolBar, QWidget

from guimauve.gui.replay_editor.icons import icons


class MainToolBar(QToolBar):
    """The application toolbar; exposes each QAction as a named attribute.

    :ivar record_action: Checkable action that starts/stops recording.
    :vartype record_action: QAction
    :ivar replay_action: Action that triggers a real (OS-driving) replay.
    :vartype replay_action: QAction
    :ivar open_action: Action that opens an existing recording file.
    :vartype open_action: QAction
    :ivar set_background_action: Checkable action that toggles the live
        screen capture on the canvas background.
    :vartype set_background_action: QAction
    :ivar save_action: Action that persists the current recording.
    :vartype save_action: QAction
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.record_action = self.addAction(icons.RECORD, " Record")
        self.record_action.setCheckable(True)
        self.replay_action = self.addAction(icons.REPLAY, " Replay")

        self.addWidget(self._make_spacer())

        self.open_action = self.addAction(icons.OPEN, " Open")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)

        self.set_background_action = self.addAction(icons.BACKGROUND, " Set_Background")
        self.set_background_action.setCheckable(True)

        self.addWidget(self._make_spacer())

        self.save_action = self.addAction(icons.SAVE, " Save")
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)

        self.setObjectName("MainToolBar")

    @staticmethod
    def _make_spacer() -> QWidget:
        """Build an invisible expanding widget used as a toolbar spacer.

        :return: A widget with ``Expanding`` horizontal size policy,
            which pushes everything to its right toward the far side
            of the toolbar.
        """
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer
