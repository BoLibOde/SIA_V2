import importlib
import sys
import types


def _load_startup_ui_with_fake_pygame(event_batches):
    class _FakeText:
        def __init__(self, text: str) -> None:
            self._text = text

        def get_width(self) -> int:
            return max(1, len(self._text) * 8)

        def get_height(self) -> int:
            return 18

    class _FakeFont:
        def render(self, text, *_args, **_kwargs):
            return _FakeText(text)

    class _FakeScreen:
        def fill(self, *_args, **_kwargs):
            return None

        def blit(self, *_args, **_kwargs):
            return None

    class _FakeRect:
        def __init__(self, *args, **kwargs):
            self.x = args[0]
            self.y = args[1]
            self.w = args[2]
            self.h = args[3]
            self.bottom = self.y + self.h
            self.centerx = self.x + self.w // 2

    class _FakeClock:
        def tick(self, *_args, **_kwargs):
            return None

    batches = list(event_batches)

    def _event_get():
        if batches:
            return batches.pop(0)
        return []

    fake_pygame = types.ModuleType("pygame")
    fake_pygame.FULLSCREEN = 0
    fake_pygame.QUIT = 0
    fake_pygame.KEYDOWN = 1
    fake_pygame.K_ESCAPE = 27
    fake_pygame.K_RETURN = 13
    fake_pygame.K_o = ord("o")
    fake_pygame.K_f = ord("f")
    fake_pygame.K_e = ord("e")
    fake_pygame.K_s = ord("s")
    fake_pygame.K_m = ord("m")
    fake_pygame.Surface = object
    fake_pygame.Rect = _FakeRect
    fake_pygame.init = lambda: None
    fake_pygame.quit = lambda: None
    fake_pygame.font = types.SimpleNamespace(init=lambda: None, SysFont=lambda *args, **kwargs: _FakeFont())
    fake_pygame.display = types.SimpleNamespace(
        set_mode=lambda *args, **kwargs: _FakeScreen(),
        set_caption=lambda *args, **kwargs: None,
        flip=lambda: None,
    )
    fake_pygame.event = types.SimpleNamespace(get=_event_get)
    fake_pygame.draw = types.SimpleNamespace(rect=lambda *args, **kwargs: None)
    fake_pygame.time = types.SimpleNamespace(Clock=lambda: _FakeClock())

    sys.modules["pygame"] = fake_pygame
    if "device.startup_ui" in sys.modules:
        return importlib.reload(sys.modules["device.startup_ui"])
    return importlib.import_module("device.startup_ui")


def test_startup_menu_returns_mode_and_simulation_toggle() -> None:
    startup_ui = _load_startup_ui_with_fake_pygame(
        [
            [types.SimpleNamespace(type=1, key=ord("o"))],  # mode menu: online
            [types.SimpleNamespace(type=1, key=ord("m"))],  # simulation menu: with simulation
        ]
    )
    menu = startup_ui.StartupMenu(fullscreen=False)
    mode, enable_fallback = menu.run()
    assert mode == "online"
    assert enable_fallback is True


def test_startup_menu_esc_in_simulation_returns_to_mode_menu() -> None:
    startup_ui = _load_startup_ui_with_fake_pygame(
        [
            [types.SimpleNamespace(type=1, key=ord("o"))],   # mode menu first pass
            [types.SimpleNamespace(type=1, key=27)],         # simulation menu: back
            [types.SimpleNamespace(type=1, key=ord("f"))],   # mode menu second pass
            [types.SimpleNamespace(type=1, key=ord("e"))],   # simulation menu: real sensors
        ]
    )
    menu = startup_ui.StartupMenu(fullscreen=False)
    mode, enable_fallback = menu.run()
    assert mode == "offline"
    assert enable_fallback is False
