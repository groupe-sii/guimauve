from guimauve.gui.element_editor.state.cascade import (
    Resolution,
    Source,
    resolve,
    resolve_element,
    resolve_variant,
)
from guimauve.gui.element_editor.state.commands import (
    ELEMENT,
    Command,
    Group,
    SetTrial,
    SetValue,
    apply_trials,
    discard_trials,
    insert,
    move,
    remove,
)
from guimauve.gui.element_editor.state.document import Document, Trials
from guimauve.gui.element_editor.state.history import History
from guimauve.gui.element_editor.state.store import Mode, Store
from guimauve.gui.element_editor.state.test_result import TestResult, TestScope
from guimauve.gui.element_editor.state.validation import Issue, Severity, can_save, validate
from guimauve.gui.element_editor.state.variants import (
    VariantSummary,
    copy_name,
    duplicate,
    new_name,
    normalize_name,
)
