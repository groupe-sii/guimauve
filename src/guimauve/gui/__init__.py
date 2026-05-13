import os

# Silence the DPI awareness warning if it hasn't been set yet
if "QT_LOGGING_RULES" not in os.environ:
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
