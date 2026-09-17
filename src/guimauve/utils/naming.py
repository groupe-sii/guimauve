import keyword
import re
from typing import Optional

_DATASET_NAME = re.compile(r"[a-z][a-z0-9]*(_[a-z0-9]+)*")
_ENTRY_NAME = re.compile(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*")


def is_valid_dataset_name(name: str) -> bool:
    return bool(_DATASET_NAME.fullmatch(name)) and not keyword.iskeyword(name)


def is_valid_entry_name(key: str) -> bool:
    return bool(_ENTRY_NAME.fullmatch(key))


def dataset_name_error(name: str) -> Optional[str]:
    if keyword.iskeyword(name):
        return f"{name!r} is a reserved Python keyword"
    if not _DATASET_NAME.fullmatch(name):
        return f"{name!r} must be a lowercase snake_case identifier"
    return None
