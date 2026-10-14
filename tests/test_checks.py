import pytest

from guimauve.checks import CheckFailure, EnvironmentCheckError


def test_error_keeps_failures():
    failures = [CheckFailure("scaling", "expected 100%, got 125%")]
    error = EnvironmentCheckError(failures)
    assert error.failures == failures


def test_error_is_a_runtime_error():
    with pytest.raises(RuntimeError):
        raise EnvironmentCheckError([CheckFailure("scaling", "x")])


def test_message_singular():
    message = str(EnvironmentCheckError([CheckFailure("scaling", "expected 100%, got 125%")]))
    assert "(1 failure)" in message
    assert "  - scaling: expected 100%, got 125%" in message


def test_message_lists_every_failure():
    message = str(
        EnvironmentCheckError(
            [
                CheckFailure("screen_size", "expected 1920x1080, got 1280x720"),
                CheckFailure("datasets", "'login' is outdated"),
            ]
        )
    )
    assert "(2 failures)" in message
    assert "screen_size: expected 1920x1080, got 1280x720" in message
    assert "datasets: 'login' is outdated" in message
