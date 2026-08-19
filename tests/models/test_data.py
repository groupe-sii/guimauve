import pytest

from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.replay import Replay


def test_construction_is_always_permissive():
    Data()
    Data(image_dir="/does/not/exist", elements={})


def test_validate_passes_for_a_minimal_valid_data():
    assert Data().validate() == []


def test_validate_flags_image_dir_that_does_not_exist():
    data = Data(image_dir="/does/not/exist/at/all")
    errors = data.validate()
    assert any("must exist" in e["msg"] for e in errors)


def test_validate_flags_image_dir_that_is_not_a_directory(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")

    data = Data(image_dir=str(file_path))
    errors = data.validate()
    assert any("must be a directory" in e["msg"] for e in errors)


def test_validate_passes_for_existing_image_dir(tmp_path):
    data = Data(image_dir=str(tmp_path))
    assert data.validate() == []


def test_validate_flags_empty_elements_dict():
    data = Data(elements={})
    errors = data.validate()
    assert any("must be not empty" in e["msg"] for e in errors)


def test_validate_passes_when_elements_is_unset_or_non_empty():
    assert Data().validate() == []

    element = Element(name="foo", x=1, y=1)
    data = Data(elements={"foo": element})
    assert data.validate() == []


def test_validate_flags_replay_dir_that_does_not_exist():
    data = Data(replay_dir="/does/not/exist/at/all")
    errors = data.validate()
    assert any("must exist" in e["msg"] for e in errors)


def test_validate_flags_replay_dir_that_is_not_a_directory(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")

    data = Data(replay_dir=str(file_path))
    errors = data.validate()
    assert any("must be a directory" in e["msg"] for e in errors)


def test_validate_passes_for_existing_replay_dir(tmp_path):
    data = Data(replay_dir=str(tmp_path))
    assert data.validate() == []


def test_data_round_trip_with_elements_and_replays():
    data = Data(
        module="my_module",
        elements={"foo": Element(name="foo", x=1, y=1)},
        replays=[Replay(name="bar", path="recordings/session1.rec")],
    )

    dumped = data.to_dict()
    loaded = Data.from_dict(dumped)

    assert loaded.elements["foo"].x == 1
    assert loaded.replays[0].path == "recordings/session1.rec"


def test_from_file_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("module: foo")

    with pytest.raises(ValueError):
        Data.from_file(path)
