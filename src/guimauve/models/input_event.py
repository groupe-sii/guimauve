import time
from typing import Union

from pydantic import Field, model_validator

from guimauve import Button, Key
from guimauve.models.model import Model


class InputEvent(Model):
    t: float = Field(default_factory=time.perf_counter)
    action: str
    args: list[Union[int, Key, Button]]

    @model_validator(mode="before")
    @classmethod
    def coerce_args(cls, data):
        if not (isinstance(data, dict) and "action" in data):
            return data
        if not data.get("args"):
            return data

        arg = data["args"][0]
        if not isinstance(arg, str):
            return data

        if data["action"] in ("mouse_down", "mouse_up"):
            data["args"][0] = Button[arg]
        elif data["action"] in ("key_down", "key_up"):
            data["args"][0] = Key[arg]

        return data
