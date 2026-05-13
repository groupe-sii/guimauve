from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLineEdit
from sugar import UNDEFINED


class StrictNumericValidator(QValidator):
    def __init__(self, min_val, max_val, decimals, is_int=False):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        self.is_int = is_int

    def validate(self, input_str, pos):
        if not input_str:
            return QValidator.Intermediate, input_str, pos

        if input_str == "-":
            if self.min_val is None or self.min_val < 0:
                return QValidator.Intermediate, input_str, pos
            return QValidator.Invalid, input_str, pos

        input_str = input_str.replace(",", ".")

        try:
            if self.is_int and "." in input_str:
                return QValidator.Invalid, input_str, pos

            val = float(input_str)

            if "." in input_str and len(input_str.split(".")[1]) > self.decimals:
                return QValidator.Invalid, input_str, pos

            if self.max_val is not None and val > self.max_val:
                return QValidator.Invalid, input_str, pos

            if self.min_val is not None and val < self.min_val:
                return QValidator.Intermediate, input_str, pos

            return QValidator.Acceptable, input_str, pos
        except ValueError:
            return QValidator.Invalid, input_str, pos


class BaseLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._default = UNDEFINED

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        self.setPlaceholderText(f"DEFAULT ({default})")
        self._default = default

    @property
    def value(self):
        raise NotImplementedError

    @value.setter
    def value(self, val):
        raise NotImplementedError


class StringLineEdit(BaseLineEdit):
    @property
    def value(self):
        text = self.text().strip()
        if not text:
            return UNDEFINED
        return text

    @value.setter
    def value(self, val):
        if val is None or val is UNDEFINED:
            self.clear()
        else:
            self.setText(str(val))


class IntLineEdit(BaseLineEdit):
    def __init__(self, min_val=None, max_val=None, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.setValidator(StrictNumericValidator(min_val, max_val, 0, is_int=True))

    @property
    def value(self):
        text = self.text()
        if not text or text == "-":
            return UNDEFINED
        return int(text)

    @value.setter
    def value(self, val):
        if val is None or val is UNDEFINED:
            self.clear()
        else:
            self.setText(str(int(val)))


class FloatLineEdit(BaseLineEdit):
    def __init__(self, min_val=None, max_val=None, decimals=2, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        self.setValidator(StrictNumericValidator(min_val, max_val, decimals))

    @property
    def value(self):
        text = self.text().replace(",", ".")
        if not text or text == "-" or text == ".":
            return UNDEFINED
        try:
            return float(text)
        except ValueError:
            return UNDEFINED

    @value.setter
    def value(self, val):
        if val is None or val is UNDEFINED:
            self.clear()
        else:
            self.setText(f"{float(val):.{self.decimals}f}")
