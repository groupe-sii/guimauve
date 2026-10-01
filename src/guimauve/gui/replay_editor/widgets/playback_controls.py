"""Playback controls: time labels, position slider, play/pause and reset.

Emits high-level playback intents as signals; owns no replay logic —
the main window decides what play / pause / reset actually do.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.replay_editor.icons import icons
from guimauve.gui.replay_editor.widgets.event_track import EventTrack
from guimauve.models.input_event import InputEvent

_UNITS_PER_SECOND = 100


class PlaybackControls(QWidget):
    """Slider + event-track ticks + play/pause + reset buttons.

    :cvar play_pause_toggled: Emitted with ``True`` when playback starts,
        ``False`` when it pauses.
    :cvar reset_clicked: Emitted when the reset button is clicked.
    :cvar position_changed: Emitted with a time (in seconds) when the
        user moves the slider or clicks a tick on the event track.
    """

    play_pause_toggled = Signal(bool)
    reset_clicked = Signal()
    position_changed = Signal(float)

    def __init__(
        self,
        duration_seconds: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        :param duration_seconds: Initial duration of the recording, in
            seconds. ``None`` (the default) puts the controls in an
            empty state.
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self._build_ui()
        self.set_duration(duration_seconds)

    def _build_ui(self) -> None:
        """Assemble the child widgets and lay them out."""
        self.start_time_label = QLabel("00:00")
        self.reference_time_label = QLabel()
        self.end_time_label = QLabel()

        time_row = QHBoxLayout()
        time_row.addWidget(self.start_time_label)
        time_row.addStretch()
        time_row.addWidget(self.reference_time_label)
        time_row.addStretch()
        time_row.addWidget(self.end_time_label)
        time_row.setAlignment(Qt.AlignCenter)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.valueChanged.connect(self._on_slider_changed)

        self.event_track = EventTrack()
        self.event_track.event_clicked.connect(self._on_event_clicked)

        self.play_pause_button = QPushButton(icons.PLAY, "Play")
        self.play_pause_button.setCheckable(True)
        self.play_pause_button.setMinimumSize(20, 20)
        self.play_pause_button.setMaximumSize(100, 100)
        self.play_pause_button.clicked.connect(self._on_play_pause_clicked)

        self.reset_button = QPushButton(icons.RESET, "")
        self.reset_button.setMinimumSize(20, 20)
        self.reset_button.setMaximumSize(100, 100)
        self.reset_button.clicked.connect(self.reset_clicked)

        controls_row = QHBoxLayout()
        controls_row.addWidget(self.play_pause_button)
        controls_row.addWidget(self.reset_button)

        layout = QVBoxLayout(self)
        layout.addLayout(time_row)
        layout.addWidget(self.event_track)
        layout.addWidget(self.slider)
        layout.addLayout(controls_row)

    def set_duration(self, seconds: float | None) -> None:
        """Configure the slider range from a duration in seconds.

        :param seconds: Duration in seconds, or ``None`` / ``0`` to
            put the controls in an empty state (disabled slider,
            ``--:--`` labels).
        """
        if not seconds:
            self.slider.setEnabled(False)
            self.slider.blockSignals(True)
            self.slider.setMaximum(1)
            self.slider.setValue(0)
            self.slider.blockSignals(False)
            self.start_time_label.setText("--:--")
            self.end_time_label.setText("--:--")
            self.reference_time_label.setText("--:-- / --:--")
        else:
            self.slider.setEnabled(True)
            self.slider.setMaximum(int(seconds * _UNITS_PER_SECOND))
            self.slider.setValue(0)
            self.start_time_label.setText("00:00")
            self.end_time_label.setText(self._format(seconds))
            self._update_reference_label(0)

    def set_events(self, events: list[InputEvent]) -> None:
        """Forward an event list to the underlying :class:`EventTrack`.

        :param events: The events to draw on the timeline.
        """
        self.event_track.set_events(events)

    def set_position(self, seconds: float) -> None:
        """Move the slider programmatically, without emitting a signal.

        :param seconds: New playhead position in seconds.
        """
        self.slider.blockSignals(True)
        self.slider.setValue(int(seconds * _UNITS_PER_SECOND))
        self.slider.blockSignals(False)
        self._update_reference_label(seconds)

    def _on_event_clicked(self, seconds: float) -> None:
        """React to an event-track click: move slider and re-emit.

        :param seconds: Time of the clicked event, in seconds since the
            start of the recording.
        """
        self.set_position(seconds)
        self.position_changed.emit(seconds)

    def _on_play_pause_clicked(self) -> None:
        """Flip the button's icon/label and emit :data:`play_pause_toggled`."""
        playing = self.play_pause_button.isChecked()
        self.play_pause_button.setIcon(icons.PAUSE if playing else icons.PLAY)
        self.play_pause_button.setText("Pause" if playing else "Play")
        self.play_pause_toggled.emit(playing)

    def _on_slider_changed(self, value: int) -> None:
        """Convert the slider integer value to seconds and emit.

        :param value: Raw slider value (centiseconds).
        """
        seconds = value / _UNITS_PER_SECOND
        self._update_reference_label(seconds)
        self.position_changed.emit(seconds)

    def _update_reference_label(self, value: float) -> None:
        """Refresh the ``current / total`` label.

        :param value: Current position in seconds.
        """
        total = self.slider.maximum() / _UNITS_PER_SECOND
        self.reference_time_label.setText(f"{self._format(value)} / {self._format(total)}")

    @staticmethod
    def _format(seconds: float) -> str:
        """Format a duration as ``MM:SS``, truncating to the second.

        :param seconds: Duration in seconds.
        :return: A zero-padded ``MM:SS`` string.
        """
        total = int(seconds)
        return f"{total // 60:02}:{total % 60:02}"
