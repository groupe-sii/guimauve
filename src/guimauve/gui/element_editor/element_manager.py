from PySide6.QtCore import QObject, Signal

from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties


class ElementManager(QObject):
    element_loaded = Signal(object, object)
    variant_added = Signal(object)
    variant_selected = Signal(object)
    variant_removed = Signal(object, object)

    def __init__(self):
        super().__init__()

        self.element = None
        self.current_variant = None

    def load(self, element: Element, default: DefaultProperties):
        self.element = element
        self.element_loaded.emit(element, default)

    def update_properties(self, to_update: dict):
        for key, value in to_update.items():
            setattr(self.element, key, value)

    def update_variant(self, to_update: dict):
        for key, value in to_update.items():
            setattr(self.current_variant, key, value)

    def add_variant(self, variant):
        if not self.element.variants:
            self.element.variants = {}

        self.element.variants[variant.name] = variant
        self.current_variant = variant
        self.variant_added.emit(variant)

    def select_variant(self, variant):
        self.current_variant = variant
        self.variant_selected.emit(variant)

    def remove_variant(self, variant, next_variant):
        self.current_variant = next_variant
        del self.element.variants[variant.name]
        self.variant_removed.emit(variant, next_variant)

        if not self.element.variants:
            self.element.variants = None

    def add_target(self, target):
        if not self.current_variant.targets:
            self.current_variant.targets = []
        self.current_variant.targets.append(target)

    def remove_target(self, target):
        if not self.current_variant.targets:
            return
        self.current_variant.targets = [t for t in self.current_variant.targets if t is not target]
        if not self.current_variant.targets:
            self.current_variant.targets = None
