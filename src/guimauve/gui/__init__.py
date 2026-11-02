import os
import warnings

EDITOR_VARIABLE = "GUIMAUVE_EDITOR"

# Silence the DPI awareness warning if it hasn't been set yet
if "QT_LOGGING_RULES" not in os.environ:
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"


def legacy_editor_enabled() -> bool:
    """Whether GUIMAUVE_EDITOR=legacy asks for the old element editor, kept as a fallback.

    The new editor opens otherwise; a value other than legacy is reported by a warning.
    """
    value = os.environ.get(EDITOR_VARIABLE, "").strip().lower()
    if value and value != "legacy":
        warnings.warn(
            f"{EDITOR_VARIABLE}={value!r} is unknown, the new editor opens; set it to 'legacy' for the old one.",
            stacklevel=2,
        )
    return value == "legacy"
