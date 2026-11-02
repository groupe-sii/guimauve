"""Wording shared by the panels."""


def plural(count: int, word: str) -> str:
    """Count and word, e.g. "1 issue" or "3 issues"."""
    return f"{count} {word}{'' if count == 1 else 's'}"
