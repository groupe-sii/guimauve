import cv2 as cv
import numpy as np

from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.models.area import Area
from guimauve.models.parameters import VNC


def test_accepts_display_only_parameters():
    driver = VNCDriver(**VNC(host="localhost", display=1).to_dict())

    assert (driver.host, driver.display, driver.port, driver.password) == ("localhost", 1, None, None)


def test_accepts_port_only_parameters():
    driver = VNCDriver(**VNC(host="localhost", port=5901).to_dict())

    assert (driver.host, driver.display, driver.port, driver.password) == ("localhost", None, 5901, None)


def _connected_server(monkeypatch, **kwargs) -> str:
    captured = {}

    def fake_connect(server, **_):
        captured["server"] = server
        return object()

    monkeypatch.setattr("guimauve.drivers.vnc.driver.api.connect", fake_connect)
    monkeypatch.setattr(VNCDriver, "_active_clients", set())
    VNCDriver(host="localhost", **kwargs).connect()
    return captured["server"]


def test_connect_keeps_display_zero(monkeypatch):
    assert _connected_server(monkeypatch, display=0) == "localhost:0"


def test_connect_with_port_only(monkeypatch):
    assert _connected_server(monkeypatch, port=5901) == "localhost::5901"


class FakeClient:
    """Stands in for a vncdotool client: records captures and writes a small image."""

    def __init__(self):
        self.calls: list[tuple] = []

    def captureScreen(self, path):  # noqa: N802 (vncdotool API)
        self.calls.append(("captureScreen",))
        cv.imwrite(path, np.zeros((20, 30, 3), dtype=np.uint8))

    def captureRegion(self, path, x, y, w, h):  # noqa: N802 (vncdotool API)
        self.calls.append(("captureRegion", x, y, w, h))
        cv.imwrite(path, np.zeros((h, w, 3), dtype=np.uint8))


def _driver_with_fake_client() -> tuple[VNCDriver, FakeClient]:
    driver = VNCDriver(host="localhost", display=0)
    driver._client = FakeClient()
    return driver, driver._client


def test_screens_are_unknown():
    driver, _ = _driver_with_fake_client()
    assert driver.screens() == []


def test_capture_ignores_the_screen():
    driver, fake = _driver_with_fake_client()
    image = driver.capture(2)
    assert fake.calls == [("captureScreen",)]
    assert image.shape == (20, 30, 3)


def test_capture_area_uses_the_region():
    driver, fake = _driver_with_fake_client()
    image = driver.capture(2, Area(left=10, top=20, right=50, bottom=35))
    assert fake.calls == [("captureRegion", 10, 20, 40, 15)]
    assert image.shape == (15, 40, 3)
