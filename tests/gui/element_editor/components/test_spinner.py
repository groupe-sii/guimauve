import pytest

from guimauve.gui.element_editor_next.components import Spinner
from guimauve.gui.element_editor_next.components.spinner import HOP, ROSE_KEYS, VIOLET_KEYS, Pose, pose_at


def test_both_rest_at_the_start_of_the_cycle():
    assert pose_at(0.0, ROSE_KEYS) == Pose()
    assert pose_at(0.0, VIOLET_KEYS) == Pose()


@pytest.mark.parametrize(("progress", "keys"), [(0.3, ROSE_KEYS), (0.7, VIOLET_KEYS)])
def test_each_hops_in_turn(progress, keys):
    assert pose_at(progress, keys).lift == HOP


def test_landing_squashes():
    pose = pose_at(0.1, ROSE_KEYS)

    assert pose.width > 1 > pose.height


def test_cycle_repeats():
    assert pose_at(1.3, ROSE_KEYS) == pose_at(0.3, ROSE_KEYS)


def test_runs_while_shown(qtbot):
    spinner = Spinner(14)
    qtbot.addWidget(spinner)

    spinner.show()
    assert spinner.is_running()
    assert spinner.width() > spinner.height() == 14

    spinner.hide()
    assert not spinner.is_running()
