"""Preview-player subpackage.

``PreviewPlayer`` orchestrates the cursor, ripples, drags and keyboard
overlay renderers over a shared ``QGraphicsScene``, driven by a QTimer.
Individual renderers and pure event-computation helpers live in their
own modules.
"""

from guimauve.gui.replay_editor.preview.player import PreviewPlayer

__all__ = ["PreviewPlayer"]
