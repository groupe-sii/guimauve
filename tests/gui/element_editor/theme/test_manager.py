import pytest
from PySide6.QtCore import QSettings, QSize
from PySide6.QtGui import QPalette

from guimauve.gui.element_editor_next.theme import DARK, LIGHT, TYPE, Icon, ThemeChoice, ThemeManager
from guimauve.gui.element_editor_next.theme import manager as manager_module


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def system(monkeypatch):
    """Simulated system scheme: set system.dark, then call system.notify() as the system would."""

    class System:
        dark = False
        callbacks: list = []

        def notify(self):
            for callback in self.callbacks:
                callback()

    fake = System()
    monkeypatch.setattr(manager_module, "is_dark_scheme", lambda: fake.dark)
    monkeypatch.setattr(manager_module, "watch_scheme", fake.callbacks.append)
    return fake


@pytest.fixture
def make_manager(qapp, settings, system):
    def make() -> ThemeManager:
        return ThemeManager(qapp, settings)

    yield make
    qapp.setStyleSheet("")
    qapp.setPalette(QPalette())


@pytest.fixture
def changes():
    """Counts the changed signals of a manager."""

    def count(manager: ThemeManager) -> list[None]:
        emitted: list[None] = []
        manager.changed.connect(lambda: emitted.append(None))
        return emitted

    return count


def test_system_by_default(make_manager):
    assert make_manager().choice is ThemeChoice.SYSTEM


def test_choice_is_kept(make_manager):
    make_manager().set_choice(ThemeChoice.DARK)
    assert make_manager().choice is ThemeChoice.DARK


def test_invalid_choice_falls_back_to_system(make_manager, settings):
    settings.setValue("theme", "pink")
    assert make_manager().choice is ThemeChoice.SYSTEM


def test_choice_wins_over_the_system(make_manager, system):
    system.dark = True
    manager = make_manager()
    manager.set_choice(ThemeChoice.LIGHT)
    assert manager.palette is LIGHT


def test_system_choice_follows_the_system(make_manager, system, changes):
    manager = make_manager()
    manager.apply()
    emitted = changes(manager)

    system.dark = True
    system.notify()

    assert manager.palette is DARK
    assert len(emitted) == 1


def test_system_change_is_ignored_with_a_fixed_choice(make_manager, system, changes):
    manager = make_manager()
    manager.apply()
    manager.set_choice(ThemeChoice.LIGHT)
    emitted = changes(manager)

    system.dark = True
    system.notify()

    assert emitted == []


def test_same_effective_theme_emits_nothing(make_manager, changes):
    manager = make_manager()
    emitted = changes(manager)
    manager.set_choice(ThemeChoice.LIGHT)  # the system is light
    assert emitted == []


def test_apply_styles_the_application(qapp, make_manager):
    manager = make_manager()
    manager.set_choice(ThemeChoice.DARK)
    manager.apply()
    assert qapp.palette().color(QPalette.ColorRole.Window).name().upper() == DARK.background
    assert DARK.surface in qapp.styleSheet()
    assert qapp.font().family() == TYPE.family


def test_icon_takes_the_color_of_the_role(make_manager):
    pixmap = make_manager().icon(Icon.X, "accent").pixmap(QSize(24, 24))
    image = pixmap.toImage()
    assert image.pixelColor(12, 12).name().upper() == LIGHT.accent
