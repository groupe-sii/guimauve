import pytest

from guimauve.storage.workspace import DataWorkspace


@pytest.fixture
def workspace(tmp_path):
    """A DataWorkspace rooted in a temp dir, with one empty dataset ready."""
    ws = DataWorkspace(tmp_path / ".guimauve")
    ws.create_dataset("app")
    return ws
