import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from guimauve.detection import ocr as ocr_module
from guimauve.detection.ocr import Ocr
from guimauve.enums import OcrFidelity


def _fresh_ocr():
    instance = object.__new__(Ocr)
    Ocr.__init__(instance)
    return instance


class _NonReentrantEngine:
    """Fails the test if two predictions overlap, like a non thread-safe native engine would crash."""

    def __init__(self):
        self.active = 0
        self.max_active = 0
        self._counter_lock = threading.Lock()

    def predict(self, _image):
        with self._counter_lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.01)
        with self._counter_lock:
            self.active -= 1
        return []


def test_engine_is_created_once_and_never_used_concurrently(monkeypatch):
    created = []

    def fake_paddle_ocr(**_):
        time.sleep(0.01)
        engine = _NonReentrantEngine()
        created.append(engine)
        return engine

    monkeypatch.setattr(ocr_module, "PaddleOCR", fake_paddle_ocr)
    ocr = _fresh_ocr()
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: ocr._readtext(image, OcrFidelity.FAST), range(16)))

    assert len(created) == 1
    assert created[0].max_active == 1
