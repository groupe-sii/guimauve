from typing import Optional

from sugar import Schema


class Replay(Schema):
    name: Optional[str]
    replay: str
