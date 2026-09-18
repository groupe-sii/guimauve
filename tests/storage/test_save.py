import json

import numpy as np

from guimauve.enums import Key
from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.input_event import InputEvent
from guimauve.models.replay import Replay
from guimauve.models.variant import ImageVariant
from guimauve.storage.save import save_element, save_replay

# --- save_element ---


def test_save_element_writes_image_and_frees_it(workspace):
    variant = ImageVariant(image=np.zeros((2, 2, 3), dtype="uint8"))
    element = Element(name="LOGIN", variants={"DEFAULT": variant})

    save_element(workspace, "app", element)

    expected = workspace.image_path("app", "LOGIN", "DEFAULT")
    assert expected.is_file()  # image persisted to the canonical path
    assert variant.path == expected  # path updated on the variant
    assert variant.image is None  # ndarray freed


def test_save_element_registers_in_data_file(workspace):
    variant = ImageVariant(image=np.zeros((2, 2, 3), dtype="uint8"))
    element = Element(name="LOGIN", variants={"DEFAULT": variant})

    save_element(workspace, "app", element)

    data = Data.from_file(workspace.data_file("app"))
    assert "LOGIN" in data.elements
    assert data.resolve() == []  # the written data.yml is valid


# --- save_replay ---


def _replay(name="RUN_1"):
    return Replay(
        name=name,
        events=[
            InputEvent(t=0.0, action="key_down", args=[Key.A]),
            InputEvent(t=0.1, action="key_up", args=[Key.A]),
        ],
    )


def test_save_replay_writes_events_and_frees_them(workspace):
    replay = _replay()

    save_replay(workspace, "app", replay)

    expected = workspace.replay_path("app", "RUN_1")
    assert expected.is_file()  # events persisted to the canonical path
    assert replay.path == expected  # path updated on the replay
    assert replay.events is None  # events freed


def test_save_replay_serializes_events_as_json(workspace):
    replay = _replay()

    save_replay(workspace, "app", replay)

    with workspace.replay_path("app", "RUN_1").open() as f:
        data = json.load(f)

    assert data == [
        {"t": 0.0, "action": "key_down", "args": ["A"]},
        {"t": 0.1, "action": "key_up", "args": ["A"]},
    ]


def test_save_replay_registers_in_data_file(workspace):
    save_replay(workspace, "app", _replay())

    data = Data.from_file(workspace.data_file("app"))
    assert "RUN_1" in data.replays
    assert data.resolve() == []  # the written data.yml is valid
