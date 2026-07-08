"""Pygame-based boot screen shown before the main app starts.

The user selects between **Online-Modus** and **Offline-Modus** using:

* The mood-input buttons (if GPIO is available):
    - **GUT-Taste**         → Online-Modus
    - **NEUTRAL- / SCHLECHT-Taste** → Offline-Modus
* Keyboard fallback:
    - **O** or **Enter**    → Online-Modus
    - **F**                 → Offline-Modus
    - **ESC** / window close → stay in menu (keep choosing)

``run()`` blocks until the user makes a selection and returns ``"online"`` or
``"offline"``.  After returning, pygame is still initialised so that
``DeviceUI.__init__`` can call ``pygame.display.set_mode()`` without re-init.
"""

import pygame

# ── colour palette (matches DeviceUI dark theme) ──────────────────────────────
_BG = (18, 20, 28)
_CARD = (30, 34, 46)
_BORDER = (55, 62, 82)
_TEXT = (220, 225, 235)
_SUBTLE = (120, 130, 155)
_HIGHLIGHT = (80, 160, 240)
_OK = (60, 200, 100)
_WARN = (220, 170, 40)


class StartupMenu:
    """Display a mode-selection screen and return the chosen mode string.

    Parameters
    ----------
    width, height:
        Display resolution (should match ``DeviceConfig.display_*``).
    fullscreen:
        Pass ``True`` on the real Pi; ``False`` during development.
    good_pin, neutral_pin, bad_pin:
        BCM GPIO pin numbers for the three mood buttons.
    """

    def __init__(
        self,
        width: int = 1024,
        height: int = 600,
        fullscreen: bool = True,
        good_pin: int = 27,
        neutral_pin: int = 22,
        bad_pin: int = 17,
    ) -> None:
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self._good_pin = good_pin
        self._neutral_pin = neutral_pin
        self._bad_pin = bad_pin

        # GPIO is optional – silently skip when hardware is unavailable
        self._gpio = None
        self._prev_gpio: dict[str, int] = {}
        try:
            import RPi.GPIO as GPIO  # type: ignore[import]

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(good_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(neutral_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(bad_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._prev_gpio = {
                "good": GPIO.input(good_pin),
                "neutral": GPIO.input(neutral_pin),
                "bad": GPIO.input(bad_pin),
            }
            self._gpio = GPIO
        except (ImportError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> str:
        """Show the menu until the user picks a mode.  Returns ``'online'`` or ``'offline'``."""
        pygame.init()
        pygame.font.init()

        flags = pygame.FULLSCREEN if self.fullscreen else 0
        screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("SIA – Betriebsmodus wählen")

        title_font = pygame.font.SysFont("arial", 36, bold=True)
        option_font = pygame.font.SysFont("arial", 30, bold=True)
        hint_font = pygame.font.SysFont("arial", 19)

        clock = pygame.time.Clock()

        while True:
            # ── keyboard / window events ──────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Window close button – stay in menu (do nothing)
                    pass
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_o, pygame.K_RETURN):
                        return "online"
                    elif event.key == pygame.K_f:
                        return "offline"
                    # ESC → stay in menu (requirement: "Menü wiederholen")

            # ── GPIO button polling ───────────────────────────────────
            gpio_result = self._poll_gpio()
            if gpio_result is not None:
                return gpio_result

            # ── rendering ─────────────────────────────────────────────
            screen.fill(_BG)
            self._draw_title(screen, title_font, hint_font)
            self._draw_options(screen, option_font, hint_font)
            self._draw_key_hints(screen, hint_font)
            pygame.display.flip()
            clock.tick(30)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _poll_gpio(self) -> str | None:
        """Return ``'online'`` / ``'offline'`` on a button press, else ``None``."""
        if self._gpio is None:
            return None
        GPIO = self._gpio
        pins = {
            "good": self._good_pin,
            "neutral": self._neutral_pin,
            "bad": self._bad_pin,
        }
        for mood, pin in pins.items():
            current = GPIO.input(pin)
            prev = self._prev_gpio.get(mood, GPIO.HIGH)
            self._prev_gpio[mood] = current
            if prev == GPIO.HIGH and current == GPIO.LOW:
                return "online" if mood == "good" else "offline"
        return None

    def _draw_title(self, screen: pygame.Surface, title_font, hint_font) -> None:
        title = title_font.render("SIA Stimmungs-bar-o-meter", True, _TEXT)
        subtitle = hint_font.render("Bitte Betriebsmodus wählen:", True, _SUBTLE)
        cx = self.width // 2
        screen.blit(title, (cx - title.get_width() // 2, 70))
        screen.blit(subtitle, (cx - subtitle.get_width() // 2, 125))

    def _draw_options(self, screen: pygame.Surface, option_font, hint_font) -> None:
        cx = self.width // 2
        card_w, card_h = 280, 130
        gap = 40

        # ── Online card ───────────────────────────────────────────────
        online_rect = pygame.Rect(cx - card_w - gap // 2, 185, card_w, card_h)
        pygame.draw.rect(screen, _CARD, online_rect, border_radius=18)
        pygame.draw.rect(screen, _HIGHLIGHT, online_rect, width=3, border_radius=18)

        ot = option_font.render("Online-Modus", True, _TEXT)
        screen.blit(ot, (online_rect.centerx - ot.get_width() // 2, online_rect.y + 28))

        ob = hint_font.render("[ GUT-Taste / O ]", True, _OK)
        screen.blit(ob, (online_rect.centerx - ob.get_width() // 2, online_rect.y + 82))

        # ── Offline card ──────────────────────────────────────────────
        offline_rect = pygame.Rect(cx + gap // 2, 185, card_w, card_h)
        pygame.draw.rect(screen, _CARD, offline_rect, border_radius=18)
        pygame.draw.rect(screen, _BORDER, offline_rect, width=3, border_radius=18)

        ft = option_font.render("Offline-Modus", True, _TEXT)
        screen.blit(ft, (offline_rect.centerx - ft.get_width() // 2, offline_rect.y + 28))

        fb = hint_font.render("[ NEUTRAL / SCHLECHT / F ]", True, _WARN)
        screen.blit(fb, (offline_rect.centerx - fb.get_width() // 2, offline_rect.y + 82))

        # ── Description texts below cards ─────────────────────────────
        desc_y = online_rect.bottom + 28
        descs = [
            (online_rect.centerx, "Server-Verbindung · Retry-Buffer", _SUBTLE),
            (offline_rect.centerx, "Nur lokal · kein Server", _SUBTLE),
        ]
        for x, text, color in descs:
            s = hint_font.render(text, True, color)
            screen.blit(s, (x - s.get_width() // 2, desc_y))

    def _draw_key_hints(self, screen: pygame.Surface, hint_font) -> None:
        hint = hint_font.render(
            "Tastatur:  [O] Online   [F] Offline   [ESC] Menü wiederholen",
            True,
            _SUBTLE,
        )
        screen.blit(hint, (self.width // 2 - hint.get_width() // 2, self.height - 50))
