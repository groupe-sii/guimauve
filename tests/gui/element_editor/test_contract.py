import numpy as np
import pytest

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.contract import Context, EditorResult, ResumeMode
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters


def context() -> Context:
    return Context(Element(name="button"), Parameters().default, lambda screen: np.zeros((1, 1, 3), np.uint8))


@pytest.mark.parametrize(
    ("mode", "delay"),
    [
        (ResumeMode.NOW, 0),
        (ResumeMode.AFTER_3_S, 3),
        (ResumeMode.AFTER_5_S, 5),
        (ResumeMode.AFTER_10_S, 10),
        (ResumeMode.PAUSED, None),
    ],
)
def test_resume_delay(mode, delay):
    assert mode.delay == delay


def test_resume_mode_is_read_back_from_its_value():
    assert all(ResumeMode(mode.value) is mode for mode in ResumeMode)


def test_context_defaults_to_the_cli():
    opened = context()

    assert (opened.message, opened.action) == ("", "")
    assert opened.code_overrides == {}
    assert opened.screens == []
    assert not opened.from_run


def test_contexts_do_not_share_their_defaults():
    first, second = context(), context()
    first.code_overrides["timeout"] = 5
    first.screens.append(Screen(0, 0, 1920, 1080))

    assert second.code_overrides == {}
    assert second.screens == []


def test_result_resumes_now_by_default():
    assert EditorResult(None).resume is ResumeMode.NOW
