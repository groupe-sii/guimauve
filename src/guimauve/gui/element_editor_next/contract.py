"""What the editor receives and returns; the caller saves, the editor never does."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy

from guimauve.drivers.driver import Screen
from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties


class ResumeMode(Enum):
    """How the run resumes once the editor is closed, by Save or Skip; the value is stored in the settings."""

    NOW = "now"
    AFTER_3_S = "3s"
    AFTER_5_S = "5s"
    AFTER_10_S = "10s"
    PAUSED = "paused"

    @property
    def delay(self) -> float | None:
        """Seconds to wait before resuming; None to stay paused until the tester resumes."""
        return _DELAYS[self]


_DELAYS: dict[ResumeMode, float | None] = {
    ResumeMode.NOW: 0.0,
    ResumeMode.AFTER_3_S: 3.0,
    ResumeMode.AFTER_5_S: 5.0,
    ResumeMode.AFTER_10_S: 10.0,
    ResumeMode.PAUSED: None,
}


@dataclass
class Context:
    """What the editor needs to open.

    :param element: Element to edit, without the overrides set in the code.
    :param default: Default values, from the configuration file; read-only.
    :param capture_provider: Captures a screen by its number, as Driver.capture.
    :param message: Why the editor opened, e.g. the detection message; empty from the CLI.
    :param action: Action in progress when the editor opened; empty from the CLI.
    :param code_overrides: Values set in the code for this call, by field name.
    :param screens: Screens of the driver, as Driver.screens(); empty when unknown, as with VNC.
    :param from_run: Opened during a run, which resumes afterwards; from the CLI otherwise.
    """

    element: Element
    default: DefaultProperties
    capture_provider: Callable[[int], numpy.ndarray]
    message: str = ""
    action: str = ""
    code_overrides: dict[str, Any] = field(default_factory=dict)
    screens: list[Screen] = field(default_factory=list)
    from_run: bool = False


@dataclass(frozen=True)
class EditorResult:
    """What the editor returns.

    :param element: Edited element to save, images still in memory; None on Skip or Cancel.
    :param resume: How the run resumes; meaningless from the CLI.
    """

    element: Element | None
    resume: ResumeMode = ResumeMode.NOW
