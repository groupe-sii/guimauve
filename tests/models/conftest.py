import pytest


@pytest.fixture
def real_file(tmp_path):
    p = tmp_path / "file"
    p.write_bytes(b"")
    return p
