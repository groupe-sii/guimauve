from guimauve.detection.ocr import Ocr


def test_case_insensitive():
    assert Ocr._similarity("Code", "code") == 1.0
