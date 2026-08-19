from typing import Annotated, Optional

from pydantic import model_validator

from guimauve.models.base import Bounds, Model, strict_only


class VNC(Model):
    host: str
    display: Annotated[Optional[int], Bounds(min=0)] = None
    # Port 0 means "any" for a socket to bind, not something to connect to — exclude it.
    port: Annotated[Optional[int], Bounds(min=1, max=65535)] = None
    password: Optional[str] = None

    @model_validator(mode="after")
    @strict_only
    def _display_or_port_required(self, info):
        if self.display is None and self.port is None:
            raise ValueError("at least a display or a port must be specified")
        return self
