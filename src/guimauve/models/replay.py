from pathlib import Path
from typing import Optional, Union

from guimauve.models.base import Model


class Replay(Model):
    name: Optional[str] = None
    path: Union[Path, str]
