"""Text cut to fit a width: on two lines between words, else ending with an ellipsis."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


def fit_text(text: str, metrics: QFontMetrics, width: int, lines: int = 2) -> str:
    """The text as it fits in width: unchanged, then wrapped between words on up to lines, then elided.

    A word is never cut in the middle to wrap: a word too long for its line ends with an ellipsis instead.
    """
    if width <= 0 or metrics.horizontalAdvance(text) <= width:
        return text
    words = text.split()
    result: list[str] = []
    while words and len(result) < lines - 1:
        line = words.pop(0)
        while words and metrics.horizontalAdvance(f"{line} {words[0]}") <= width:
            line = f"{line} {words.pop(0)}"
        result.append(line)
    if words:
        result.append(" ".join(words))
    return "\n".join(metrics.elidedText(line, Qt.TextElideMode.ElideRight, width) for line in result)
