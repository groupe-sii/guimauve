from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import cv2 as cv

from guimauve.detection.detector import Match, Point
from guimauve.enums import Button, ScreenArea
from guimauve.models.parameters.screenshot import Screenshot
from guimauve.models.variant import Variant

SPECIALS = "/", "\\", ".", "?", "*"


def log_screenshot(
    context: Screenshot,
    current_action: str,
    args: tuple,
    kwargs: dict,
    variant: Optional[Variant],
    screenshot: Callable,
    mouse_position: Point,
    result: Optional[list[Match]],
) -> None:
    """
    Save an annotated screenshot with the mouse position.
    If an element is specified, the search area and matches are also highlighted.
    The file name includes the action and timestamp.

    :param context: The screenshot parameters.
    :param current_action: The action performed.
    :param args: The positional arguments of the action.
    :param kwargs: The keyword arguments of the action.
    :param variant: The variant of the action.
    :param screenshot: The screenshot provider.
    :param mouse_position: The mouse position.
    :param result: The result of the action.
    """
    if not context.enable:
        return

    if current_action == "wait":
        return

    for action, to_shoot in context.on.to_dict().items():
        if action == current_action and not to_shoot:
            return

    now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
    detail = None

    folder = Path(context.folder)
    folder.mkdir(parents=True, exist_ok=True)

    screen = screenshot()

    cv.circle(screen, center=mouse_position, radius=5, color=(255, 0, 0), thickness=-1)

    if current_action == "locate":
        if area := variant.search_area:
            if isinstance(area, ScreenArea):
                h, w, _ = screen.shape
                area = area.get_area((w, h))
            cv.rectangle(screen, area.tl, area.br, color=(0, 255, 0), thickness=2)
        for match in result:
            if match.box:
                cv.rectangle(screen, match.box.tl, match.box.br, color=(255, 0, 0), thickness=2)
            if match.target:
                x, y = match.target
                size = 10
                cv.line(screen, (x - size, y), (x + size, y), color=(255, 0, 0), thickness=2)
                cv.line(screen, (x, y - size), (x, y + size), color=(255, 0, 0), thickness=2)

    elif current_action == "click":
        current_action = f"{kwargs.get('button', Button.LEFT).name.lower()}_{current_action}"

    elif current_action == "type":
        detail = args[0]
        for special in SPECIALS:
            detail = detail.replace(special, "")
        if len(detail) >= 2:
            detail = f"{detail[0]}xxx"

    elif current_action == "press":
        detail = "_".join(key.name for key in args)

    if variant and variant.name:
        detail = variant.name

    file_name = f"{now}_{current_action}"
    if detail:
        file_name += f"_{detail}"

    file_name = f"{file_name}.png"
    path = folder / file_name

    if context.limit:
        n_screenshot = sum(1 for _ in folder.glob("*.png"))
        if n_screenshot >= context.limit:
            next(folder.glob("*.png")).unlink()

    cv.imwrite(str(path), cv.cvtColor(screen, cv.COLOR_RGB2BGR))
