import logging
import platform
from dataclasses import dataclass

import yaml

from guimauve.drivers.driver import Driver
from guimauve.storage.sync import FORMAT_VERSION, compute_source_hash, read_module_constants
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.screen import get_primary_scaling

logger = logging.getLogger(__name__)

SYNC_HINT = "run `guimauve data sync`"


@dataclass(frozen=True)
class CheckFailure:
    check: str
    message: str


class EnvironmentCheckError(RuntimeError):
    def __init__(self, failures: list[CheckFailure]):
        self.failures = failures

        count = len(failures)
        title = f"Environment checks failed ({count} failure{'s' if count > 1 else ''}):"
        body = "\n".join(f"  - {f.check}: {f.message}" for f in failures)

        super().__init__(f"\n\n{title}\n{body}")


def check_datasets(workspace: DataWorkspace, selection: bool | list[str]) -> list[CheckFailure]:
    """Checks that the generated modules of the selected datasets match their data.yml."""
    if selection is False:
        return []

    aliases = workspace.datasets() if selection is True else selection
    if not aliases:
        logger.warning("Dataset check skipped: no dataset found in %s", workspace.root)
        return []

    failures = []
    for alias in aliases:
        if problem := _dataset_problem(workspace, alias):
            failures.append(CheckFailure("datasets", f"{alias!r}: {problem}"))
    return failures


def _dataset_problem(workspace: DataWorkspace, alias: str) -> str | None:
    """Returns a description of what is wrong with the dataset, or None if it is up to date."""
    if not workspace.exists(alias):
        return f"dataset not found in {workspace.root}"

    try:
        expected_hash = compute_source_hash(workspace.data_file(alias))
    except (OSError, ValueError, yaml.YAMLError) as e:
        return f"cannot read {workspace.DATA_FILE} ({e})"

    try:
        constants = read_module_constants(alias)
    except (OSError, ValueError, SyntaxError) as e:
        return f"cannot read the generated module ({e}), {SYNC_HINT}"

    if constants is None:
        return f"module not generated, {SYNC_HINT}"
    if "SOURCE_HASH" not in constants:
        return f"generated module has no SOURCE_HASH (older guimauve version), {SYNC_HINT}"
    if constants.get("FORMAT_VERSION") != FORMAT_VERSION:
        found = constants.get("FORMAT_VERSION")
        return f"generated module format is {found!r}, expected {FORMAT_VERSION!r}, {SYNC_HINT}"
    if constants["SOURCE_HASH"] != expected_hash:
        return f"{workspace.DATA_FILE} changed since the last sync, {SYNC_HINT}"
    return None


def check_screen_size(expected: tuple[int, int] | None, driver: Driver) -> list[CheckFailure]:
    """Checks that the screen seen by the driver has the expected size."""
    if expected is None:
        return []

    height, width = driver.capture().shape[:2]
    if (width, height) != tuple(expected):
        return [CheckFailure("screen_size", f"expected {expected[0]}x{expected[1]}, got {width}x{height}")]
    return []


def check_scaling(expected: int | None, execution_mode: str) -> list[CheckFailure]:
    """Checks the display scaling of the primary monitor (local mode on Windows only)."""
    if expected is None:
        return []

    if execution_mode != "local" or platform.system() != "Windows":
        logger.warning("Scaling check skipped: only supported in local mode on Windows")
        return []

    try:
        actual = get_primary_scaling()
    except OSError as e:
        logger.warning("Scaling check skipped: cannot read the display scaling (%s)", e)
        return []

    if actual != expected:
        return [CheckFailure("scaling", f"expected {expected}%, got {actual}%")]
    return []
