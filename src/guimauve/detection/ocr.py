import logging
import os
import re
from functools import wraps
from math import sqrt

import cv2 as cv
import easyocr
import numpy as np
from PIL import Image
from textdistance.algorithms.edit_based import levenshtein

from guimauve.detection.detector import Detector


def handle_images(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        image1 = args[0]
        image2 = args[1]

        if isinstance(image1, str):
            with open(image1, "rb") as i:
                image1 = cv.imdecode(np.asarray(bytearray(i.read())), cv.IMREAD_UNCHANGED)
        if isinstance(image2, str):
            with open(image2, "rb") as i:
                image2 = cv.imdecode(np.asarray(bytearray(i.read())), cv.IMREAD_UNCHANGED)

        if isinstance(image1, Image.Image):
            image1 = np.array(image1)
        if isinstance(image2, Image.Image):
            image2 = np.array(image2)

        return func(image1, image2, **kwargs)

    return wrapper


class Ocr(Detector):
    """
    This class implements an image detection algorithm based on OCR (Optical Character Recognition).
    It also provides methods to locate a given text in an image or returns all text data in an image.
    """

    FILTER_LIST = "aàbcdeéèêëfghiïjklmnoôpqrstuùvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'- "

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        dir_path = os.path.dirname(os.path.abspath(__file__))
        ocr_path = os.path.join(dir_path, "models")

        self.reader = easyocr.Reader(
            ["en", "fr"],
            recog_network="latin_g2",
            gpu=False,
            download_enabled=False,
            model_storage_directory=ocr_path,
            verbose=False,
        )

    def compute(self, needle, haystack, target, params):
        confidence_threshold = params["confidence_threshold"]

        needle_matches = self.reader.readtext(
            np.array(needle), ycenter_ths=0, min_size=0, add_margin=0, link_threshold=0.42, allowlist=Ocr.FILTER_LIST
        )
        if not needle_matches:
            return []

        text = Ocr._matches_to_string(needle_matches)
        top_left_offset = Ocr._get_first_word_location(needle_matches)[0][0]
        bot_right_loc = Ocr._get_last_word_location(needle_matches)[0][2]
        needle_height, needle_width = needle.shape[:2]
        bot_right_offset = needle_width - bot_right_loc[0], needle_height - bot_right_loc[1]

        locations = self.locate_text_on_image(haystack, text)

        if not locations:
            return []

        matches = []
        for loc in locations:
            left = loc[0][0] - top_left_offset[0]
            top = loc[0][1] - top_left_offset[1]
            width = top_left_offset[0] + bot_right_loc[0] + bot_right_offset[0]
            height = top_left_offset[1] + bot_right_loc[1] + bot_right_offset[1]

            # fmt: off
            matches.append(
                (
                    [
                        (left, top),
                        (left + width, top),
                        (left + width, top + height),
                        (left, top + height)
                    ],
                    (left + target[0], top + target[1]),
                    confidence_threshold
                )
            )
            # fmt: on

        return matches

    def read_text_on_image(self, image, area=None):
        """
        Reads text in a given image

        :param image: Image path or object
        :type image: np.ndarray
        :param area: Specifies the area to read, defaults to None
        :type area: None
                    | tuple (int <top_left_x>, int <top_left_y>, int <width>, int <height>)
                    | tuple (tuple (int <top_left_x>, int <top_left_y>), tuple (int <bot_right_x>, int <bot_right_y>))
        :return: The extracted text from the image
        :rtype: str
        """
        if area:
            x, y, w, h = area[0], area[1], area[2], area[3]
            image = image[y : y + h, x : x + w]

        return "\n".join(self.reader.readtext(image, detail=0, paragraph=True))

    def locate_text_on_image(self, image, text, area=None, search="first"):
        """
        Returns the location of a given text in an image

        :param image: Image path or object
        :type image: np.ndarray
        :param text: The text to search
        :type text: str
        :param area: Specifies the area to search, defaults to None
        :type area: None
                    | tuple (int <top_left_x>, int <top_left_y>, int <width>, int <height>)
                    | tuple (tuple (int <top_left_x>, int <top_left_y>), tuple (int <bot_right_x>, int <bot_right_y>))
        :param search: "first" to sort results by location, "best" by confidence, defaults to "first"
        :type search: str
        :return: The location of the text
        :rtype: list [list [int <top_left_x>, int <top_left_y>], list [int <bot_right_x>, int <bot_right_y>]]
        """
        text = re.sub(r" +", " ", text)
        text = text.strip().split(" ")

        if area:
            x, y, w, h = area[0], area[1], area[2], area[3]
            image = image[y : y + h, x : x + w]
        else:
            area = (0, 0)

        matches = self.reader.readtext(
            image, ycenter_ths=0, min_size=0, add_margin=0, link_threshold=0.42, allowlist=Ocr.FILTER_LIST
        )
        if not matches:
            return []

        matches = [(loc, word.strip(), conf) for loc, word, conf in matches]

        matched_words = []
        for idx, word in enumerate(text):
            matched_words.append([])
            for loc, res, conf in matches:
                if self._are_similar(word.lower(), res.lower()):
                    matched_words[idx].append([res, loc, conf])

        if [] in matched_words:
            self.logger.info(f'The word "{text[matched_words.index([])]}" is not found by OCR')
            return []

        if len(matched_words) == 1:
            words = matched_words[0]
            if search == "best":
                words = sorted(words, key=lambda x: x[2], reverse=True)
            return [
                (
                    (int(word[1][0][0] + area[0]), int(word[1][0][1] + area[1])),
                    (int(word[1][2][0] + area[0]), int(word[1][2][1] + area[1])),
                )
                for word in words
            ]

        goods = self._find(matched_words)[1]
        goods = [self._get_words_box(good) for good in goods]
        if area:
            goods = [
                ((good[0][0] + area[0], good[0][1] + area[1]), (good[1][0] + area[0], good[1][1] + area[1]))
                for good in goods
            ]

        return goods

    def _find(self, matched_words, index=0, words=None, goods=None):
        if not words:
            words = []

        if not goods:
            goods = []

        if index == len(matched_words):
            return True, words

        for word, loc, _ in matched_words[index]:
            if index == 0 or self._are_close_enough(words[-1], loc):
                ret = self._find(matched_words, index + 1, words + [loc], goods)
                if ret[0]:
                    goods.append(ret[1])
                else:
                    goods = ret[1]

        return False, goods

    @staticmethod
    def _are_similar(w1, w2, confidence=None):
        """
        Returns True if 2 words have enough similarity, else False

        :param w1: The first word
        :type w1: str
        :param w2: The second word
        :type w2: str
        :param confidence: Similarity threshold, between 0 & 1
        :type confidence: int | float
        :return: Returns True if the 2 words have enough similarity, else False
        :rtype: bool
        """
        dist = levenshtein.distance(w1, w2)
        length = max(len(w1), len(w2))
        if not confidence:
            confidence = 1 - 1 / length if length <= 6 else 0.85
        return 1 - dist / length >= confidence

    @staticmethod
    def _distance(a, b):
        """
        Returns the distance between 2 points

        :param a: The first point
        :type a: list [int <x>, int <y>]
        :param b: The second point
        :type b: list [int <x>, int <y>]
        :return: The distance between the 2 points
        :rtype: float
        """
        return sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

    @staticmethod
    def _get_center(a, b):
        """
        Returns the location of the center between 2 points

        :param a: The first point
        :type a: list [int <x>, int <y>]
        :param b: The second point
        :type b: list [int <x>, int <y>]
        :return: The location of the center between the 2 points
        :rtype: list [int <x>, int <y>]
        """
        x = (a[0] + b[0]) / 2
        y = (a[1] + b[1]) / 2
        return x, y

    @staticmethod
    def _get_first_word_location(matches):
        return min(matches, key=lambda x: x[0][0][0] + x[0][0][1])

    @staticmethod
    def _get_last_word_location(matches):
        return max(matches, key=lambda x: x[0][2][0] + x[0][2][1])

    @staticmethod
    def _matches_to_string(matches):
        matches = [[*match, Ocr._get_center(match[0][0], match[0][2])] for match in matches]
        res = []
        while matches:
            first_word = Ocr._get_first_word_location(matches)
            matches.remove(first_word)

            others = sorted([match for match in matches if match[3][1] < first_word[0][2][1]], key=lambda x: x[3][0])
            for match in others:
                matches.remove(match)

            res.append(" ".join([first_word[1]] + [other[1] for other in others]))

        return "\n".join(res)

    @staticmethod
    def _are_close_enough(w1, w2):
        """
        Returns True if the 2 words are close enough, False if not

        :param w1: Boxes of the first word
        :type w1: list [
                      list [int <x_top_left>, int <y_top_left>],
                      list [int <x_top_right>, int <y_top_right>],
                      list [int <x_bottom_right>, int <y_bottom_right>],
                      list [int <x_bottom_left>, int <y_bottom_left>]
                  ]
        :param w2: Boxes of the second word
        :type w2: list [
                      list [int <x_top_left>, int <y_top_left>],
                      list [int <x_top_right>, int <y_top_right>],
                      list [int <x_bottom_right>, int <y_bottom_right>],
                      list [int <x_bottom_left>, int <y_bottom_left>]
                  ]
        :return: True if close enough, False if not
        :rtype: bool
        """
        average_height = (abs(w1[0][1] - w1[2][1]) + abs(w2[0][1] - w2[2][1])) / 2
        w1_right = Ocr._get_middle_right(w1)
        w2_left = Ocr._get_middle_left(w2)
        distance = Ocr._distance(w1_right, w2_left)

        return distance < average_height

    @staticmethod
    def _get_middle_left(word):
        """
        Returns the location of the middle of the left side of the word box

        :param word: The word box
        :type word: list [
                        list [int <x_top_left>, int <y_top_left>],
                        list [int <x_top_right>, int <y_top_right>],
                        list [int <x_bottom_right>, int <y_bottom_right>],
                        list [int <x_bottom_left>, int <y_bottom_left>]
                    ]
        :return: The middle of the left side
        :rtype: list [int <x>, int <y>]
        """
        return [int(i) for i in (word[0][0], (word[0][1] + word[3][1]) / 2)]

    @staticmethod
    def _get_middle_right(word):
        """
        Returns the location of the middle of the right side of the word box

        :param word: The word box
        :type word: list [
                        list [int <x_top_left>, int <y_top_left>],
                        list [int <x_top_right>, int <y_top_right>],
                        list [int <x_bottom_right>, int <y_bottom_right>],
                        list [int <x_bottom_left>, int <y_bottom_left>]
                    ]
        :return: The middle of the right side
        :rtype: list [int <x>, int <y>]
        """
        return [int(i) for i in (word[1][0], (word[1][1] + word[2][1]) / 2)]

    @staticmethod
    def _get_words_box(words):
        """
        Returns the merger of multiple words box

        :param words: List of words box
        :type words: list [
                         list [int <x_top_left>, int <y_top_left>],
                         list [int <x_top_right>, int <y_top_right>],
                         list [int <x_bottom_right>, int <y_bottom_right>],
                         list [int <x_bottom_left>, int <y_bottom_left>]
                     ]
        :return: One box containing all the words
        :rtype: tuple (tuple (int <x_top_left>, int <y_top_left>), tuple (int <x_top_left>, int <y_bottom_right>)]
        """
        all_y = [loc[1] for locs in words for loc in locs]
        x1 = words[0][0][0]
        y1 = min(all_y)
        x2 = words[-1][1][0]
        y2 = max(all_y)
        return (int(x1), int(y1)), (int(x2), int(y2))

    def _get_filter_string(self, image):
        return Ocr._matches_to_string(
            self.reader.readtext(
                np.array(image), ycenter_ths=0, min_size=0, add_margin=0, link_threshold=0.42, allowlist=Ocr.FILTER_LIST
            )
        )
