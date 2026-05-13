import abc
from collections import namedtuple

import cv2
import numpy as np
from PIL import Image

from guimauve.enums import MatchSort
from guimauve.metaclass import SingletonABC

Match = namedtuple("Match", ["box", "target", "confidence"])
Box = namedtuple("Box", ["tl", "tr", "br", "bl"])
Point = namedtuple("Point", ["x", "y"])


class Detector(metaclass=SingletonABC):
    """
    Abstract base class for image detection algorithms.
    You need to override the compute method if you want to implement a new detection algorithm.
    """

    def locate(self, needle, haystack, target=None, area=None, limit=1, match_sort=MatchSort.XY_POSITION, params=None):
        """
        Locate the needle in the haystack image

        :param needle: Needle image
        :type needle: str | np.ndarray | PIL.Image
        :param haystack: Haystack image
        :type haystack: str | np.ndarray | PIL.Image
        :param target: Target point in the needle image, defaults to None
        :type target: tuple[int <x>, int <y>] | None
        :param area: Area of the haystack image to search in, defaults to None
        :type area: tuple[int <top_left_x>, int <top_left_y>, int <width>, int <height>] | None
        :param limit: Maximum number of matches to return, if -1 returns all, defaults to 1
        :type limit: int
        :param match_sort: Order to sort the matches, defaults to "MatchSort.XY_POSITION"
        :type match_sort: MatchSort
        :param params: Additional parameters
        :type params: dict | None
        :return: List of matches
        :rtype:
            | list[
            |   Match(
            |     box=Box(
            |       tl=Point(int <top_left_x>, int <top_left_y>),
            |       tr=Point(int <top_right_x>, int <top_right_y>),
            |       br=Point(int <bottom_right_x>, int <bottom_right_y>),
            |       bl=Point(int <bottom_left_x>, int <bottom_left_y>)
            |     ),
            |     target=Point(int <target_x>, int <target_y>),
            |     confidence=float <confidence>
            |   )
            | ]
        """
        needle = self.convert(needle)
        haystack = self.convert(haystack)

        self.validate(needle, haystack)

        if area is not None:
            haystack = haystack[area[1] : area[1] + area[3], area[0] : area[0] + area[2]]
        else:
            area = (0, 0)

        if target is None:
            target = (needle.shape[1] // 2, needle.shape[0] // 2)

        matches = self.compute(needle, haystack, target, params)
        matches = self.sort(matches, match_sort)
        matches = self.format(matches, area)

        if limit == -1:
            return matches

        return matches[:limit]

    @staticmethod
    def convert(image):
        """
        Convert an image to cv2 format

        :param image: Image to convert
        :type image: str | np.ndarray | PIL.Image
        :raises TypeError: If unsupported image type
        :return: Converted image
        :rtype: np.ndarray
        """
        if isinstance(image, str):
            image = cv2.imread(image)
        elif isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif not isinstance(image, np.ndarray):
            raise TypeError(f"Unsupported image type: {type(image)}")

        return image

    @staticmethod
    def validate(needle, haystack):
        """
        Validate the images to ensure they are not None and the needle is smaller than the haystack

        :param needle: Needle image
        :type needle: np.ndarray
        :param haystack: Haystack image
        :type haystack: np.ndarray
        :raises ValueError: If one or both images are None or if the needle is larger than the haystack
        """
        if needle is None or haystack is None:
            raise ValueError("One or both images could not be loaded")

        if needle.shape[0] > haystack.shape[0] or needle.shape[1] > haystack.shape[1]:
            raise ValueError("The needle image must be smaller than the haystack image")

    @abc.abstractmethod
    def compute(self, needle, haystack, target, params):
        """
        Find the needle in the haystack image
        To override when implementing a new detection algorithm

        :param needle: Needle image
        :type needle: np.ndarray
        :param haystack: Haystack image
        :type haystack: np.ndarray
        :param target: Focus point in the needle image
        :type target: tuple[int <x>, int <y>]
        :param params: Additional parameters
        :type params: dict
        :raises NotImplementedError: If not implemented
        :return: List of matches
        :rtype:
            | list[
            |   list[
            |       (int <top_left_x>, int <top_left_y>),
            |       (int <top_right_x>, int <top_right_y>),
            |       (int <bottom_right_x>, int <bottom_right_y>),
            |       (int <bottom_left_x>, int <bottom_left_y>)
            |     ],
            |     (int <target_x>, int <target_y>),
            |     float <confidence>
            |   ]
            | ]
        """
        raise NotImplementedError()

    @staticmethod
    def sort(matches, order_by):
        """
        Sort the matches based on the specified order

        :param matches: List of matches
        :type matches: list
        :param order_by: Order to sort by
        :type order_by: MatchSort
        :return: Sorted matches
        :rtype: list
        """
        if order_by == MatchSort.CONFIDENCE:
            return sorted(matches, key=lambda x: x[2], reverse=True)
        if order_by == MatchSort.XY_POSITION:
            return sorted(matches, key=lambda x: x[1][0] + x[1][1])

    @staticmethod
    def format(matches, area):
        """
        Format the matches and include the area offset

        :param matches: List of matches
        :type matches: list
        :param area: Area offset
        :type area: tuple[int <top_left_x>, int <top_left_y>, int <width>, int <height>]
        :return: List of formated matches
        :rtype:
            | list[
            |   Match(
            |     box=Box(
            |       tl=Point(int <top_left_x>, int <top_left_y>),
            |       tr=Point(int <top_right_x>, int <top_right_y>),
            |       br=Point(int <bottom_right_x>, int <bottom_right_y>),
            |       bl=Point(int <bottom_left_x>, int <bottom_left_y>)
            |     ),
            |     element=Point(int <target_x>, int <target_y>),
            |     confidence=float <confidence>
            |   )
            | ]
        """
        return [
            Match(
                box=Box(
                    tl=Point(int(match[0][0][0] + area[0]), int(match[0][0][1] + area[1])),
                    tr=Point(int(match[0][1][0] + area[0]), int(match[0][1][1] + area[1])),
                    br=Point(int(match[0][2][0] + area[0]), int(match[0][2][1] + area[1])),
                    bl=Point(int(match[0][3][0] + area[0]), int(match[0][3][1] + area[1])),
                ),
                target=Point(int(match[1][0] + area[0]), int(match[1][1] + area[1])),
                confidence=float(match[2]),
            )
            for match in matches
        ]

    @staticmethod
    def show(image, matches):
        """
        Display the image with detected matches

        :param image: Image to display
        :type image: str | np.ndarray | PIL.Image
        :param matches: List of matches
        :type matches: list
        """
        image = Detector.convert(image)
        for match in matches:
            cv2.polylines(
                image,
                pts=[np.array([match.box.tl, match.box.tr, match.box.br, match.box.bl], np.int32)],
                isClosed=True,
                color=(0, 255, 0),
                thickness=2,
            )
            cv2.circle(image, match.target, 3, (0, 0, 255), -1)
        cv2.imshow("Detected", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return image
