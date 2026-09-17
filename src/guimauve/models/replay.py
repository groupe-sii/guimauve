from pathlib import Path
from typing import Optional

from pydantic import PrivateAttr, field_validator
from pydantic_core import PydanticCustomError

from guimauve.models.model import Model


class Replay(Model):
    name: Optional[str] = None
    path: Path

    _alias: Optional[str] = PrivateAttr(default=None)
    _is_new: bool = PrivateAttr(default=False)
    _resolved: bool = PrivateAttr(default=False)

    @property
    def alias(self) -> Optional[str]:
        return self._alias

    @property
    def is_new(self) -> bool:
        return self._is_new

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v):
        if v is not None and not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v

    @field_validator("path", mode="after")
    @classmethod
    def _path_exists(cls, v):
        if not v.is_file():
            raise PydanticCustomError("file_not_found", "File does not exist", {"path": str(v)})
        return v
