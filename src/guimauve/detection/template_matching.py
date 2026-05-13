import cv2
import numpy as np

from guimauve.detection.detector import Detector


class TemplateMatching(Detector):
    """
    This class implements an image detection algorithm based on template matching
    """

    def compute(self, needle, haystack, target, params):
        grayscale = params["grayscale"]
        confidence_threshold = params["confidence_threshold"]

        if grayscale:
            needle = cv2.cvtColor(needle, cv2.COLOR_BGR2GRAY)
            haystack = cv2.cvtColor(haystack, cv2.COLOR_BGR2GRAY)

        needle_h, needle_w = needle.shape[:2]
        target_x, target_y = target

        res = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= confidence_threshold)

        matches = []
        for pt in zip(*loc[::-1]):
            conf = res[pt[1], pt[0]]
            x1, y1 = pt
            x2, y2 = x1 + needle_w, y1 + needle_h
            matches.append(((x1, y1, x2, y2), conf))

        matches.sort(key=lambda x: x[1], reverse=True)

        selected = []
        for box, conf in matches:
            keep = True
            for sel_box, _ in selected:
                if self._intersection(box, sel_box) > 0.1:
                    keep = False
                    break

            if keep:
                selected.append((box, conf))

        # fmt: off
        return [
            [
                [
                    (x1, y1),
                    (x2, y1),
                    (x2, y2),
                    (x1, y2)
                ],
                (x1 + target_x, y1 + target_y),
                round(float(conf), 2)
            ]
            for (x1, y1, x2, y2), conf in selected
        ]
        # fmt: on

    @staticmethod
    def _intersection(box1, box2):
        """
        Compute the intersection area of two bounding boxes

        :param box1: Bounding box A as (x1, y1, x2, y2)
        :type box1: tuple[int, int, int, int]
        :param box2: Bounding box B as (x1, y1, x2, y2)
        :type box2: tuple[int, int, int, int]
        :return: Overlap ratio between the two boxes, in range [0.0, 1.0]
        :rtype: float
        """

        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])

        intersection_area = max(0, x_right - x_left) * max(0, y_bottom - y_top)
        if intersection_area == 0:
            return 0.0

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union_area = area1 + area2 - intersection_area

        return intersection_area / union_area
