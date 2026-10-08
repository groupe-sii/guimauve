from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.models.parameters import VNC


def test_accepts_display_only_parameters():
    driver = VNCDriver(**VNC(host="localhost", display=1).to_dict())

    assert (driver.host, driver.display, driver.port, driver.password) == ("localhost", 1, None, None)


def test_accepts_port_only_parameters():
    driver = VNCDriver(**VNC(host="localhost", port=5901).to_dict())

    assert (driver.host, driver.display, driver.port, driver.password) == ("localhost", None, 5901, None)
