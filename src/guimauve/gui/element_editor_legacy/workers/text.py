from PySide6.QtCore import QThread

from guimauve.detection.ocr import Ocr


class TextWorker(QThread):
    def __init__(self, screenshot, text, params):
        super().__init__()

        self.screenshot = screenshot
        self.text = text
        self.params = params

        self.results = None

    def run(self):
        ocr = Ocr()
        self.results = ocr.locate_text_on_image(
            self.screenshot,
            self.text,
            fidelity=self.params["fidelity"],
            confidence_threshold=self.params["confidence_threshold"],
        )
