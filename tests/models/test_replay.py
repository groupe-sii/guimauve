import pytest

from guimauve.models.replay import Replay


def test_replay_requires_the_path_field():
    with pytest.raises(Exception):
        Replay()

    replay = Replay(path="recordings/session1.rec")
    assert replay.path == "recordings/session1.rec"
    assert replay.name is None


def test_replay_round_trip():
    replay = Replay(name="my_replay", path="recordings/session1.rec")
    dumped = replay.to_dict()
    loaded = Replay.from_dict(dumped)
    assert loaded == replay
