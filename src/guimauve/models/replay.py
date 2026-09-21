import json
from pathlib import Path
from typing import Optional

from pydantic import Field, PrivateAttr, field_validator, model_validator
from pydantic_core import PydanticCustomError

from guimauve.models.input_event import InputEvent
from guimauve.models.model import Model


class Replay(Model):
    name: str = Field(exclude=True)
    path: Optional[Path] = None
    events: Optional[list[InputEvent]] = Field(default=None, exclude=True)

    _alias: Optional[str] = PrivateAttr(default=None)
    _is_new: bool = PrivateAttr(default=False)
    _resolved: bool = PrivateAttr(default=False)

    @property
    def alias(self) -> Optional[str]:
        return self._alias

    @property
    def is_new(self) -> bool:
        return self._is_new

    @property
    def resolved(self) -> bool:
        return self._resolved

    def load(self):
        if self.events is None:
            with self.path.open("r") as f:
                data = json.load(f)
            events = []
            for d in data:
                event = InputEvent(**d)
                event.resolve()
                events.append(event)
            self.events = events
        return self

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v):
        if not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v

    @field_validator("path", mode="after")
    @classmethod
    def _path_exists(cls, v):
        if v is not None and not v.is_file():
            raise PydanticCustomError("file_not_found", "File does not exist", {"path": str(v)})
        return v

    @model_validator(mode="after")
    def _require_path_or_events(self):
        if self.path is None and not self.events:
            raise PydanticCustomError("no_source", "A replay must have a path or events")
        return self
