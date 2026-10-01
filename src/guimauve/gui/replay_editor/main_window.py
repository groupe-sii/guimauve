"""Main application window.

Wires the toolbar, canvases, playback controls, preview player and
services together. Owns app-level logic (file I/O, screen capture) but
delegates recording / real replay to the services and preview rendering
to :class:`PreviewPlayer`.
"""

import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication, Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from guimauve.enums import Key
from guimauve.gui.replay_editor.icons import icons
from guimauve.gui.replay_editor.preview import PreviewPlayer
from guimauve.gui.replay_editor.widgets.playback_controls import PlaybackControls
from guimauve.gui.replay_editor.widgets.screen_canvas import ScreenCanvas
from guimauve.gui.replay_editor.widgets.tool_bar import MainToolBar
from guimauve.gui.replay_editor.workers.recording_service import RecordingService
from guimauve.gui.replay_editor.workers.replay_service import ReplayService
from guimauve.models.input_event import InputEvent
from guimauve.models.replay import Replay
from guimauve.storage.workspace import DataWorkspace

IS_WINDOWS = sys.platform.startswith("win")


class MainWindow(QMainWindow):
    """Top-level window of the replay editor.

    Two modes:

    * **Standalone** — ``replay=None``: user records or opens from
      disk, Save writes to the workspace.
    * **CLI** — ``replay=<Replay>``: pre-loaded editor, Save flips
      :attr:`to_save` and closes so the caller can persist.

    :ivar replay: The currently-edited recording, or ``None`` until
        one is loaded / recorded.
    :vartype replay: Optional[Replay]
    :ivar to_save: Set to ``True`` when the user asked to save.
        The CLI caller reads it after :meth:`close`.
    :vartype to_save: bool
    """

    def __init__(self, replay: Replay | None = None) -> None:
        """
        :param replay: Pre-loaded recording (CLI mode) or ``None`` to
            start in standalone mode.
        """
        super().__init__()
        self.setWindowTitle("Record & Replay")

        self.replay: Replay | None = replay
        self.to_save: bool = False
        self.workspace = DataWorkspace()
        self.alias: str = "default"

        self.primary_screen = QGuiApplication.primaryScreen()
        geo = self.primary_screen.geometry()
        dpr = self.primary_screen.devicePixelRatio()
        self.screen_width = int(geo.width() * dpr)
        self.screen_height = int(geo.height() * dpr)

        self._build_toolbar()
        self._build_status_bar()
        self._build_canvases()
        self._build_playback_controls()
        self._build_central_widget()

        self.preview_player = PreviewPlayer(
            self.screen_canvas.scene(),
            overlay=self.screen_canvas.overlay(),
            parent=self,
        )
        self.preview_player.time_changed.connect(self.playback_controls.set_position)
        self.preview_player.finished.connect(self._on_preview_finished)
        self.playback_controls.play_pause_toggled.connect(self._on_preview_play_pause)
        self.playback_controls.reset_clicked.connect(self._on_preview_reset)
        self.playback_controls.position_changed.connect(self.preview_player.set_time)

        self.recording = RecordingService(self)
        self.recording.stopped.connect(self._on_record_stopped)
        self.replayer = ReplayService(self)
        self.replayer.finished.connect(self._on_replay_finished)

        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self._update_frame)

        self._load_settings()

        if replay is not None:
            if not replay.events and replay.path is not None:
                loaded = replay.load()
            else:
                loaded = replay
            self.replay = loaded
            self._set_events(loaded.events or [])
            if loaded.alias:
                self.alias = loaded.alias
            self.status.showMessage(f"Loaded replay '{loaded.name}'", 3000)

    def _build_toolbar(self) -> None:
        """Instantiate the toolbar and connect each action."""
        self.tool_bar = MainToolBar()
        self.addToolBar(self.tool_bar)

        self.tool_bar.record_action.triggered.connect(self._toggle_record)
        self.tool_bar.replay_action.triggered.connect(self._start_replay)
        self.tool_bar.open_action.triggered.connect(self._open_file)
        self.tool_bar.save_action.triggered.connect(self._save)
        self.tool_bar.set_background_action.triggered.connect(self._toggle_background)

    def _build_status_bar(self) -> None:
        """Instantiate the status bar and register it with the window."""
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _build_canvases(self) -> None:
        """Instantiate the screen canvas at physical screen resolution."""
        self.screen_canvas = ScreenCanvas(self.screen_width, self.screen_height)

    def _build_playback_controls(self) -> None:
        """Instantiate the playback controls in an empty state."""
        self.playback_controls = PlaybackControls()

    def _build_central_widget(self) -> None:
        """Assemble the central widget: canvas above, controls below."""
        content_layout = QVBoxLayout()
        content_layout.addWidget(self.screen_canvas, stretch=1)
        content_layout.addWidget(self.playback_controls)

        content = QWidget()
        content.setLayout(content_layout)

        root = QVBoxLayout()
        root.addWidget(content)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

    def _toggle_record(self) -> None:
        """Start a recording session; ESC ends it via the service signal.

        The toolbar button is checkable, but only the service is
        allowed to end recording — so if the user clicks the button
        again it re-checks itself and does nothing.
        """
        if not self.tool_bar.record_action.isChecked():
            self.tool_bar.record_action.setChecked(True)
            return

        self.showMinimized()
        self.recording.start(stop_key=Key.ESC)
        self.status.showMessage("Recording… (press ESC to stop)", 0)

    def _on_record_stopped(self) -> None:
        """Slot: the recording service signalled the session ended.

        Restores the window, wraps the captured events in a
        :class:`Replay` if there was none yet, and pushes them into
        the widgets.
        """
        events = self.recording.events
        if self.replay is None:
            self.replay = Replay(name="untitled", events=list(events))
        self._set_events(events)
        self.tool_bar.record_action.setChecked(False)
        self._restore_window()
        self.status.showMessage(f"Recorded {len(events)} events", 3000)

    def _start_replay(self) -> None:
        """Hand the current events to :class:`ReplayService`."""
        if self.replay is None or not self.replay.events:
            self.status.showMessage("Nothing to replay", 2000)
            return
        self.showMinimized()
        self.replayer.start(list(self.replay.events))

    def _on_replay_finished(self) -> None:
        """Slot: the replay service signalled the replay ended.

        Brings the window back to the foreground and shows a status
        message.
        """
        self._restore_window()
        self.status.showMessage("Replay finished", 2000)

    def _restore_window(self) -> None:
        """Un-minimize the window and force it back to the foreground.

        Called after recording or replay, when another app had focus.
        A plain :meth:`showNormal` isn't enough on Windows once focus
        was stolen — we also need to clear the minimized flag, raise
        and activate.
        """
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()

    def _save(self) -> None:
        """CLI mode: flag for save then close.

        The caller (``start_replay_editor``) reads :attr:`to_save`
        after the window closes and persists via the workspace.
        """
        if self.replay is None or not self.replay.events:
            self.status.showMessage("Nothing to save", 2000)
            return
        self.to_save = True
        self.close()

    def _open_file(self) -> None:
        """Prompt for a recording file and load it into the editor."""
        default_dir = ""
        if self.workspace.exists(self.alias):
            default_dir = str(self.workspace.replays_dir(self.alias))
        path, _ = QFileDialog.getOpenFileName(self, "Open recording", default_dir, "*.json")
        if not path:
            return
        replay = Replay(name=Path(path).stem, path=Path(path)).load()
        self.replay = replay
        self._set_events(replay.events)
        self.status.showMessage(f"Loaded {len(replay.events)} events", 2000)

    def _toggle_background(self) -> None:
        """Enable or disable live screen capture on the canvas background."""
        if self.tool_bar.set_background_action.isChecked():
            self._exclude_from_capture()
            self.capture_timer.start(100)
        else:
            self.capture_timer.stop()
            self.screen_canvas.show_placeholder()

    def _update_frame(self) -> None:
        """Timer callback: grab one frame and push it to the canvas."""
        pixmap = self.primary_screen.grabWindow(0)
        pixmap.setDevicePixelRatio(1.0)
        self.screen_canvas.show_frame(pixmap)

    def _exclude_from_capture(self) -> None:
        """Hide this window from screen captures.

        Windows only — a no-op everywhere else, since ``ctypes.windll``
        doesn't exist on other OSes.
        """
        if not IS_WINDOWS:
            return
        hwnd = int(self.winId())
        wda_exclude_from_capture = 0x11
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, wda_exclude_from_capture)

    def _on_preview_play_pause(self, playing: bool) -> None:
        """Slot: forward the toolbar's play/pause toggle to the preview.

        :param playing: ``True`` to play, ``False`` to pause.
        """
        if playing:
            self.preview_player.play()
        else:
            self.preview_player.pause()

    def _on_preview_reset(self) -> None:
        """Slot: reset the preview to time 0."""
        self.preview_player.reset()

    def _on_preview_finished(self) -> None:
        """Slot: the preview reached the end; reset the play/pause button."""
        self.playback_controls.play_pause_button.setChecked(False)
        self.playback_controls.play_pause_button.setIcon(icons.PLAY)
        self.playback_controls.play_pause_button.setText("Play")

    def _load_settings(self) -> None:
        """Restore window geometry and state from the OS-native store.

        On Windows this uses the registry, on macOS a plist file, on
        Linux an INI in ``~/.config``. Falls back to a sensible default
        size on the very first run.
        """
        settings = QSettings("Guimauve", "ReplayEditor")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(800, 500)

        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def _save_settings(self) -> None:
        """Persist current window geometry and state to the OS-native store."""
        settings = QSettings("Guimauve", "ReplayEditor")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save geometry before Qt actually closes the window.

        :param event: The Qt close event.
        """
        self._save_settings()
        super().closeEvent(event)

    def _set_events(self, events: list[InputEvent]) -> None:
        """Push a new event list into every widget that consumes them.

        :param events: The events to load. Also stored on
            :attr:`replay`, which must not be ``None``.
        """
        if self.replay is None:
            return
        self.replay.events = list(events)
        if self.replay.events:
            duration = self.replay.events[-1].t - self.replay.events[0].t
            self.playback_controls.set_duration(max(1.0, duration))
        else:
            self.playback_controls.set_duration(None)
        self.playback_controls.set_events(self.replay.events)
        self.preview_player.set_events(self.replay.events)
