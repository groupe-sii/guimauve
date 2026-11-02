from PySide6.QtCore import QThread

from guimauve.detection.ocr import Ocr


class OcrWorker(QThread):
    def __init__(self, screenshot, to_find, params):
        super().__init__()

        self.screenshot = screenshot
        self.to_find = to_find
        self.params = params

        self.results = None

    def run(self):
        ocr = Ocr()
        self.results = ocr.locate(self.to_find, self.screenshot, params=self.params, limit=10)
