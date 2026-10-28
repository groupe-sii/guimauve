"""Banner of the trials, under the tabs of the inspector."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import Button, ElidedLabel, Variant
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.panels.wording import plural
from guimauve.gui.element_editor_next.state import Mode, Store
from guimauve.gui.element_editor_next.theme import METRICS

TEST_MODE = "Test mode · {trials}"
KEPT = "{trials} kept for the Test"
APPLY_TIP = "Write the trial values into the element"
DISCARD_TIP = "Forget the trial values"


class TrialBanner(QFrame):
    """In Test mode, the count of trials with Discard and Apply, disabled without trials; in Edit mode, a line
    telling the trials are kept, shown only when there are some.
    """

    def __init__(self, store: Store, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("trialBanner")
        self._store = store
        self.text = ElidedLabel()
        self.discard = Button("Discard")
        self.discard.setToolTip(DISCARD_TIP)
        self.discard.clicked.connect(store.discard_trials)
        self.apply = Button("Apply", Variant.PRIMARY)
        self.apply.setToolTip(APPLY_TIP)
        self.apply.clicked.connect(store.apply_trials)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(3), METRICS.space(2), METRICS.space(3), METRICS.space(2))
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self.text, 1)
        layout.addWidget(self.discard)
        layout.addWidget(self.apply)

        store.document_changed.connect(self.refresh)  # the trials go through the history
        store.mode_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        store = self._store
        count = _count(store)
        testing = store.mode is Mode.TEST
        trials = plural(count, "trial value") if count else "no trial value"
        self.setVisible(testing or count > 0)
        self.text.setText(TEST_MODE.format(trials=trials) if testing else KEPT.format(trials=trials))
        set_style_property(self.text, "muted", not testing)
        for button in (self.discard, self.apply):
            button.setVisible(testing)
            button.setEnabled(count > 0)


def _count(store: Store) -> int:
    trials, keys = store.document.trials, store.variant_keys()
    return len(trials.element) + sum(len(values) for key, values in trials.variants.items() if key in keys)
