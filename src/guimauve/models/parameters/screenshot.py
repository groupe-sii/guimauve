from pathlib import Path
from typing import Annotated, Optional, Union

from guimauve.models.base import Bounds, Model


class ScreenshotActions(Model):
    locate: bool = True
    move: bool = True
    click: bool = True
    scroll: bool = True
    type: bool = True
    press: bool = True


class Screenshot(Model):
    enable: bool = False
    folder: Union[Path, str] = Path("screenshots")
    limit: Annotated[Optional[int], Bounds(min=0)] = None
    on: ScreenshotActions = ScreenshotActions()
