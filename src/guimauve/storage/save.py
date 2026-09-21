import json

import cv2 as cv

from guimauve.models.data import Data
from guimauve.models.variant import ImageVariant
from guimauve.storage.workspace import DataWorkspace


def save_element(workspace: DataWorkspace, alias: str, element) -> None:
    data = Data.from_file(workspace.data_file(alias))
    if data.elements is None:
        data.elements = {}

    name = element.name

    for variant in element.variants or []:
        if isinstance(variant, ImageVariant) and variant.image is not None:
            path = workspace.image_path(alias, name, variant.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            cv.imwrite(str(path), cv.cvtColor(variant.image, cv.COLOR_RGB2BGR))
            variant.path = path
            variant.image = None  # free the ndarray

    data.elements[name] = element
    data.to_file(workspace.data_file(alias))


def save_replay(workspace: DataWorkspace, alias: str, replay) -> None:
    data = Data.from_file(workspace.data_file(alias))
    if data.replays is None:
        data.replays = {}

    name = replay.name

    if replay.events is not None:
        path = workspace.replay_path(alias, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump([e.to_dict(json_mode=True) for e in replay.events], f, indent=2)
        replay.path = path
        replay.events = None  # free the events

    data.replays[name] = replay
    data.to_file(workspace.data_file(alias))
