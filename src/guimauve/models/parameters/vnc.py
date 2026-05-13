from typing import Optional

from sugar import Schema


class VNC(Schema):
    host: str
    display: Optional[int] = None
    port: Optional[int] = None
    password: Optional[str] = None

    def full_validate(self):
        if self.display is None and self.port is None:
            yield "at least a display or a port must be specified"
