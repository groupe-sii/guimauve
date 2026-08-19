from pathlib import Path
from typing import Optional, Union

from pydantic import field_validator

from guimauve.models.base import Model, strict_only
from guimauve.models.element import Element
from guimauve.models.replay import Replay


class Data(Model):
    module: Optional[str] = None
    image_dir: Optional[Union[Path, str]] = None
    elements: Optional[dict[str, Element]] = None
    replay_dir: Optional[Union[Path, str]] = None
    replays: Optional[list[Replay]] = None

    @field_validator("image_dir", mode="after")
    @classmethod
    @strict_only
    def _image_dir_exists(cls, v, info):
        if v is None:
            return v

        path = Path(v)
        if not path.exists():
            raise ValueError("must exist")
        if not path.is_dir():
            raise ValueError("must be a directory")
        return v

    @field_validator("elements", mode="after")
    @classmethod
    @strict_only
    def _elements_not_empty(cls, v, info):
        if v == {}:
            raise ValueError("must be not empty")
        return v

    @field_validator("replay_dir", mode="after")
    @classmethod
    @strict_only
    def _replay_dir_exists(cls, v, info):
        if v is None:
            return v

        path = Path(v)
        if not path.exists():
            raise ValueError("must exist")
        if not path.is_dir():
            raise ValueError("must be a directory")
        return v
