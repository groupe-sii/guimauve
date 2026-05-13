from typing import Optional

from sugar import Schema

class Replay(Schema):
    name: Optional[str]
    replay_path: str

    def __init__(self, name: Optional[str], replay_path: str):
        pass

    def __call__(self, name: Optional[str], replay_path: str) -> Replay:
        pass
