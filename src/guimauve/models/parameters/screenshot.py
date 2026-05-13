from pathlib import Path
from typing import Optional, Union

from sugar import Schema


class ScreenshotActions(Schema):
    locate: bool = True
    move: bool = True
    click: bool = True
    scroll: bool = True
    type: bool = True
    press: bool = True


class Screenshot(Schema):
    enable: bool = False
    folder: Union[Path, str] = Path("screenshots")
    limit: Optional[int]
    on: ScreenshotActions = ScreenshotActions()
