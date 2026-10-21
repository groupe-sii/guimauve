"""Environment checks run at Controller startup.

Each check returns a failure message, or None when the environment matches.
"""

import logging
import platform

import yaml

from guimauve.drivers.driver import Screen
from guimauve.storage.sync import FORMAT_VERSION, compute_source_hash, read_module_constants
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.screen import get_scaling

logger = logging.getLogger(__name__)

SYNC_HINT = "run `guimauve data sync`"


class EnvironmentCheckError(RuntimeError):
    def __init__(self, failures: list[str]):
        self.failures = failures

        count = len(failures)
        title = f"Environment checks failed ({count} failure{'s' if count > 1 else ''}):"
        body = "\n".join(f"  - {failure}" for failure in failures)

        super().__init__(f"\n\n{title}\n{body}")


# --- Screen ---


def check_screen_exists(number: int, screens: list[Screen]) -> str | None:
    """Checks that a screen exists among those listed by the driver (screens[0] bounds all of them)."""
    if number < len(screens):
        return None
    count = len(screens) - 1
    return f"screen {number}: does not exist, {count} screen{'s' if count > 1 else ''} available"


def check_screen_size(number: int, expected: tuple[int, int], actual: tuple[int, int]) -> str | None:
    if tuple(expected) == tuple(actual):
        return None
    return f"screen {number}: size expected {expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}"


def check_scaling(number: int, expected: int, execution_mode: str) -> str | None:
    if execution_mode != "local" or platform.system() != "Windows":
        logger.warning("Scaling check skipped for screen %s: only supported in local mode on Windows", number)
        return None

    try:
        actual = get_scaling(number)
    except OSError as e:
        logger.warning("Scaling check skipped for screen %s: cannot read the display scaling (%s)", number, e)
        return None

    if actual == expected:
        return None
    return f"screen {number}: scaling expected {expected}%, got {actual}%"


# --- Datasets ---


def selected_datasets(workspace: DataWorkspace, selection: bool | list[str]) -> list[str]:
    """Returns the aliases to check: every dataset of the workspace if selection is True."""
    if selection is False:
        return []
    if selection is True:
        aliases = workspace.datasets()
        if not aliases:
            logger.warning("Dataset check skipped: no dataset found in %s", workspace.root)
        return aliases
    return selection


def check_dataset(workspace: DataWorkspace, alias: str) -> str | None:
    if problem := _dataset_problem(workspace, alias):
        return f"datasets: {alias!r} {problem}"
    return None


def _dataset_problem(workspace: DataWorkspace, alias: str) -> str | None:
    if not workspace.exists(alias):
        return f"not found in {workspace.root}, create it with `guimauve data add {alias}`"

    try:
        expected_hash = compute_source_hash(workspace.data_file(alias))
    except (OSError, ValueError, yaml.YAMLError) as e:
        return f"has an unreadable {workspace.DATA_FILE} ({e}), fix it then {SYNC_HINT}"

    try:
        constants = read_module_constants(alias)
    except (OSError, ValueError, SyntaxError) as e:
        return f"has an unreadable generated module ({e}), {SYNC_HINT}"

    if constants is None:
        return f"has no generated module, {SYNC_HINT}"
    if "SOURCE_HASH" not in constants:
        return f"was generated before SOURCE_HASH existed, {SYNC_HINT}"
    if constants.get("FORMAT_VERSION") != FORMAT_VERSION:
        return f"was generated with an older module format, {SYNC_HINT}"
    if constants["SOURCE_HASH"] != expected_hash:
        return f"is outdated: {workspace.DATA_FILE} changed since the last sync, {SYNC_HINT}"
    return None
