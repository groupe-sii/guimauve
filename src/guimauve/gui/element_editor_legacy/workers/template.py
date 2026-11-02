from PySide6.QtCore import QThread

from guimauve.detection.template_matching import TemplateMatching


class TemplateWorker(QThread):
    def __init__(self, screenshot, to_find, params):
        super().__init__()

        self.screenshot = screenshot
        self.to_find = to_find
        self.params = params

        self.results = None

    def run(self):
        tm = TemplateMatching()
        self.results = tm.locate(self.to_find, self.screenshot, params=self.params, limit=50)
