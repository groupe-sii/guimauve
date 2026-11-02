from PySide6.QtCore import QThread

from guimauve.detection.feature_matching import FeatureMatching


class FeatureWorker(QThread):
    def __init__(self, screenshot, to_find, params):
        super().__init__()

        self.screenshot = screenshot
        self.to_find = to_find
        self.params = params

        self.results = None

    def run(self):
        fm = FeatureMatching()
        self.results = fm.locate(self.to_find, self.screenshot, params=self.params, limit=15)
