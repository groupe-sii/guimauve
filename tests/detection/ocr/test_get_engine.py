import pytest

from guimauve.detection import ocr as ocr_module
from guimauve.detection.ocr import Ocr
from guimauve.enums import OcrFidelity


def _fresh_ocr():
    instance = object.__new__(Ocr)
    Ocr.__init__(instance)
    return instance


def test_uses_vendored_model_dir_when_present(monkeypatch, tmp_path):
    det_name, rec_name = ocr_module._PADDLE_MODELS[OcrFidelity.FAST]
    det_dir = tmp_path / "official_models" / det_name
    rec_dir = tmp_path / "official_models" / rec_name
    det_dir.mkdir(parents=True)
    rec_dir.mkdir(parents=True)
    (det_dir / "inference.json").write_text("{}")
    (rec_dir / "inference.json").write_text("{}")

    monkeypatch.setattr(ocr_module, "_MODELS_ROOT", tmp_path)

    captured = {}

    def fake_paddle_ocr(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(ocr_module, "PaddleOCR", fake_paddle_ocr)

    _fresh_ocr()._get_engine(OcrFidelity.FAST)

    assert captured["text_detection_model_dir"] == str(det_dir)
    assert captured["text_recognition_model_dir"] == str(rec_dir)
    assert captured["text_detection_model_name"] == det_name
    assert captured["text_recognition_model_name"] == rec_name


def test_raises_clear_error_when_missing_locally_and_download_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_module, "_MODELS_ROOT", tmp_path)

    def fake_paddle_ocr(**kwargs):
        raise Exception("No available model hosting platforms detected.")

    monkeypatch.setattr(ocr_module, "PaddleOCR", fake_paddle_ocr)

    with pytest.raises(RuntimeError) as exc_info:
        _fresh_ocr()._get_engine(OcrFidelity.FAST)

    assert str(tmp_path) in str(exc_info.value)
