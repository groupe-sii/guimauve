from typing import Optional

from pydantic import field_validator
from pydantic_core import PydanticCustomError

from guimauve.models.element import Element
from guimauve.models.model import Model
from guimauve.models.replay import Replay
from guimauve.utils.naming import is_valid_entry_name


class Data(Model):
    elements: Optional[dict[str, Element]] = None
    replays: Optional[dict[str, Replay]] = None

    @field_validator("elements", "replays", mode="after")
    @classmethod
    def _reject_empty(cls, v):
        if v == {}:
            raise PydanticCustomError("empty", "Input must be not empty")
        return v

    @field_validator("elements", "replays", mode="after")
    @classmethod
    def _keys_convention(cls, v):
        if not v:
            return v

        bad = [k for k in v if not is_valid_entry_name(k)]
        if bad:
            raise PydanticCustomError(
                "bad_name",
                "Keys must be UPPER_SNAKE_CASE: {names}",
                {"names": ", ".join(bad), "keys": bad},
            )

        return v
