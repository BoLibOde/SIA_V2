"""Pygame-based startup menu shown before the main app starts.

Two selections are required:
1) operating mode: online/offline
2) sensor strategy: real sensors or simulation fallback on hardware failure

``run()`` blocks until the user makes both selections and returns
``("online"|"offline", enable_simulation_fallback: bool)``. After returning,
pygame is still initialised so that ``DeviceUI.__init__`` can call
``pygame.display.set_mode()`` without re-init.
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
        except ImportError:
            pass  # No RPi.GPIO installed (development machine)
        except RuntimeError as exc:
            print(f"[StartupMenu] GPIO not available (permission/hardware error): {exc}", flush=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> tuple[str, bool]:
        """Show both startup menus and return ``(operating_mode, enable_simulation_fallback)``."""
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
            mode = self._run_mode_menu(screen, clock, title_font, option_font, hint_font)
            enable_simulation_fallback = self._run_simulation_menu(
                screen,
                clock,
                title_font,
                option_font,
                hint_font,
            )
            if enable_simulation_fallback is None:
                continue
            return mode, enable_simulation_fallback

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_mode_menu(self, screen, clock, title_font, option_font, hint_font) -> str:
        while True:
            # ── keyboard / window events ──────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Window close button exits the application –
                    # a mode *must* be chosen to proceed.
                    pygame.quit()
                    raise SystemExit(0)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_o, pygame.K_RETURN):
                        return "online"
                    elif event.key == pygame.K_f:
                        return "offline"
                    # ESC → stay in menu (requirement: "Menü wiederholen")

            # ── GPIO button polling ───────────────────────────────────
            gpio_result = self._poll_gpio("mode")
            if gpio_result is not None:
                return gpio_result

            # ── rendering ─────────────────────────────────────────────
            screen.fill(_BG)
            self._draw_mode_title(screen, title_font, hint_font)
            self._draw_mode_options(screen, option_font, hint_font)
            self._draw_mode_key_hints(screen, hint_font)
            pygame.display.flip()
            clock.tick(30)

    def _run_simulation_menu(self, screen, clock, title_font, option_font, hint_font) -> bool | None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit(0)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_e, pygame.K_RETURN):
                        return False
                    elif event.key in (pygame.K_s, pygame.K_m):
                        return True
                    elif event.key == pygame.K_ESCAPE:
                        return None

            gpio_result = self._poll_gpio("simulation")
            if gpio_result is not None:
                return gpio_result

            screen.fill(_BG)
            self._draw_simulation_title(screen, title_font, hint_font)
            self._draw_simulation_options(screen, option_font, hint_font)
            self._draw_simulation_key_hints(screen, hint_font)
            pygame.display.flip()
            clock.tick(30)

    def _poll_gpio(self, menu: str) -> str | bool | None:
        """Poll mood buttons and map to mode/simulation selection for the active menu."""
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
                if menu == "mode":
                    return "online" if mood == "good" else "offline"
                return False if mood == "good" else True
        return None

    def _draw_mode_title(self, screen: pygame.Surface, title_font, hint_font) -> None:
        title = title_font.render("SIA Stimmungs-bar-o-meter", True, _TEXT)
        subtitle = hint_font.render("Bitte Betriebsmodus wählen:", True, _SUBTLE)
        cx = self.width // 2
        screen.blit(title, (cx - title.get_width() // 2, 70))
        screen.blit(subtitle, (cx - subtitle.get_width() // 2, 125))

    def _draw_mode_options(self, screen: pygame.Surface, option_font, hint_font) -> None:
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

    def _draw_mode_key_hints(self, screen: pygame.Surface, hint_font) -> None:
        hint = hint_font.render(
            "Tastatur:  [O] Online   [F] Offline   [ESC] Menü wiederholen",
            True,
            _SUBTLE,
        )
        screen.blit(hint, (self.width // 2 - hint.get_width() // 2, self.height - 50))

    def _draw_simulation_title(self, screen: pygame.Surface, title_font, hint_font) -> None:
        title = title_font.render("Simulation auswählen", True, _TEXT)
        subtitle = hint_font.render("Soll bei Sensor-Ausfall auf Simulation gewechselt werden?", True, _SUBTLE)
        cx = self.width // 2
        screen.blit(title, (cx - title.get_width() // 2, 70))
        screen.blit(subtitle, (cx - subtitle.get_width() // 2, 125))

    def _draw_simulation_options(self, screen: pygame.Surface, option_font, hint_font) -> None:
        cx = self.width // 2
        card_w, card_h = 320, 130
        gap = 40

        real_rect = pygame.Rect(cx - card_w - gap // 2, 185, card_w, card_h)
        pygame.draw.rect(screen, _CARD, real_rect, border_radius=18)
        pygame.draw.rect(screen, _HIGHLIGHT, real_rect, width=3, border_radius=18)

        rt = option_font.render("Echte Sensoren", True, _TEXT)
        screen.blit(rt, (real_rect.centerx - rt.get_width() // 2, real_rect.y + 28))
        rb = hint_font.render("[ GUT-Taste / E / Enter ]", True, _OK)
        screen.blit(rb, (real_rect.centerx - rb.get_width() // 2, real_rect.y + 82))

        sim_rect = pygame.Rect(cx + gap // 2, 185, card_w, card_h)
        pygame.draw.rect(screen, _CARD, sim_rect, border_radius=18)
        pygame.draw.rect(screen, _BORDER, sim_rect, width=3, border_radius=18)

        st = option_font.render("Mit Simulation", True, _TEXT)
        screen.blit(st, (sim_rect.centerx - st.get_width() // 2, sim_rect.y + 28))
        sb = hint_font.render("[ NEUTRAL / SCHLECHT / M ]", True, _WARN)
        screen.blit(sb, (sim_rect.centerx - sb.get_width() // 2, sim_rect.y + 82))

    def _draw_simulation_key_hints(self, screen: pygame.Surface, hint_font) -> None:
        hint = hint_font.render(
            "Tastatur: [E] Echte Sensoren  [M/S] Mit Simulation  [ESC] Zurück zum Modus-Menü",
            True,
            _SUBTLE,
        )
        screen.blit(hint, (self.width // 2 - hint.get_width() // 2, self.height - 50))
