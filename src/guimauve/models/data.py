from pathlib import Path
from typing import Optional, Union

from sugar import Schema

from guimauve.models.element import Element
from guimauve.models.replay import Replay


class Data(Schema):
    module: Optional[str]
    image_dir: Optional[Union[Path, str]]
    elements: Optional[dict[str, Element]]
    replay_dir: Optional[Union[Path, str]]
    replays: Optional[list[Replay]]

    def validate_image_dir(self):
        path = Path(self.image_dir)
        if not path.exists():
            yield "must exist"
        elif not path.is_dir():
            yield "must be a directory"

    def validate_elements(self):
        if self.elements == {}:
            yield "must be not empty"

    def validate_replay_dir(self):
        path = Path(self.replay_dir)
        if not path.exists():
            yield "must exist"
        elif not path.is_dir():
            yield "must be a directory"

    # def full_validate(self):
    #     if self.elements is None:
    #         return
    #
    #     for name, element in self.elements.items():
    #         if element.has_coordinates():
    #             continue
    #
    #         image_path = Path(self.image_dir or ".") / element.image
    #         error_path = ["elements", f"['{name}']"]
    #
    #         if not image_path.exists():
    #             yield error_path, f"image file '{image_path}' does not exist"
    #             continue
    #         if not image_path.is_file():
    #             yield error_path, f"image file '{image_path}' is not a file"
    #             continue
    #
    #         image = cv2.imread(str(image_path))
    #
    #         if image is None:
    #             yield error_path, f"image file '{image_path}' cannot be read as an image"
    #             continue
    #         if image.size == 0:
    #             yield error_path, f"image file '{image_path}' is empty"
    #             continue
    #
    #         img_height, img_width = image.shape[:2]
    #
    #         if element.subarea:
    #             img_height, img_width = image.shape[:2]
    #             area = element.subarea
    #             if not (0 <= area.top < area.bottom <= img_height) or not (0 <= area.left < area.right <= img_width):
    #                 yield error_path, f"subarea {area} is out of image bounds ({img_width}x{img_height})"
    #                 continue
    #
    #         if area := element.screen_area:
    #             if area.width < img_width or area.height < img_height:
    #                 yield error_path, f"screen_area is smaller than image size ({img_width}x{img_height})"
