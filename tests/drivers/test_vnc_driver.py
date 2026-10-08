from guimauve.drivers.vnc.driver import VNCDriver
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
