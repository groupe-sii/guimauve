import pytest

from guimauve.drivers.local.bindings import _KEYPAD_VK, KEY_MAP, key_from_pynput


@pytest.mark.parametrize("key", list(_KEYPAD_VK))
def test_keypad_keys_round_trip(key):
    """A keypad key pressed by the driver is recorded as the same key, with the codes of the current system."""
    assert key_from_pynput(KEY_MAP[key]) is key
