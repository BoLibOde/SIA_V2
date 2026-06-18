from pathlib import Path

import pygame

from device.gpio_handler import MoodCounts
from device.models import SensorReading

# German labels for mood status displayed in the smiley card
_MOOD_LABELS = {"good": "GUT", "neutral": "NEUTRAL", "bad": "SCHLECHT"}


class DeviceUI:
    def __init__(self, width: int, height: int, fullscreen: bool = True, device_id: str = "") -> None:
        pygame.init()
        pygame.font.init()

        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("SIA Stimmungs-bar-o-meter")

        self.width = width
        self.height = height
        self.device_id = device_id

        # Dark theme
        self.bg_color = (18, 20, 28)
        self.card_color = (30, 34, 46)
        self.border_color = (55, 62, 82)
        self.text_color = (220, 225, 235)
        self.subtle_color = (120, 130, 155)
        self.ok_color = (60, 200, 100)
        self.warn_color = (220, 170, 40)
        self.err_color = (220, 80, 70)

        self.title_font = pygame.font.SysFont("arial", 34, bold=True)
        self.label_font = pygame.font.SysFont("arial", 24, bold=True)
        self.value_font = pygame.font.SysFont("arial", 30)
        self.status_font = pygame.font.SysFont("arial", 18)

        assets_dir = Path(__file__).parent / "assets"
        self.smileys = {
            "good": self._load_smiley(assets_dir / "good.png"),
            "neutral": self._load_smiley(assets_dir / "meh.png"),
            "bad": self._load_smiley(assets_dir / "bad.png"),
        }

        # Keyboard-triggered action flags – reset at the start of each handle_events() call.
        # To add physical GPIO buttons for these actions, poll the button states in main.py
        # alongside these flags (e.g. gpio_handler.pending_upload / pending_daily_reset).
        self.action_upload: bool = False
        self.action_reset_daily: bool = False

    def _load_smiley(self, path: Path) -> pygame.Surface:
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, (220, 220))

    def handle_events(self) -> bool:
        """Process pygame events. Returns False if the app should quit.

        Sets action_upload=True when U is pressed (manual upload flush).
        Sets action_reset_daily=True when R is pressed (refresh today's server counts).
        Both flags are cleared at the start of each call; they are True for one frame only.
        """
        self.action_upload = False
        self.action_reset_daily = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_u:
                    self.action_upload = True
                elif event.key == pygame.K_r:
                    self.action_reset_daily = True
        return True

    def draw(
        self,
        reading: SensorReading | None,
        counts: MoodCounts,
        pending_counts: MoodCounts | None = None,
        server_connected: bool = False,
        last_upload_status: str = "—",
    ) -> None:
        status = self._pick_status(counts)

        self.screen.fill(self.bg_color)
        self._draw_title()
        self._draw_sensor_card(reading)
        self._draw_counts_card(counts, pending_counts)
        self._draw_smiley_card(status)
        self._draw_status_bar(server_connected, last_upload_status)
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()

    def _pick_status(self, counts: MoodCounts) -> str:
        if counts.good > counts.bad and counts.good >= counts.neutral:
            return "good"
        if counts.bad > counts.good and counts.bad >= counts.neutral:
            return "bad"
        return "neutral"

    def _draw_title(self) -> None:
        title = self.title_font.render("SIA Stimmungs-bar-o-meter", True, self.text_color)
        self.screen.blit(title, (40, 25))

    def _draw_sensor_card(self, reading: SensorReading | None) -> None:
        rect = pygame.Rect(40, 90, 430, 250)
        self._draw_card(rect)

        title = self.label_font.render("Live Sensor-Werte", True, self.text_color)
        self.screen.blit(title, (60, 115))

        if reading is None:
            text = self.value_font.render("Keine Sensordaten", True, self.subtle_color)
            self.screen.blit(text, (60, 190))
            return

        temp = self.value_font.render(f"Temperatur: {reading.temperature_c:.1f} °C", True, self.text_color)
        hum = self.value_font.render(f"Luftfeuchte: {reading.humidity_pct:.1f} %", True, self.text_color)
        co2 = self.value_font.render(f"CO2: {reading.co2_ppm} ppm", True, self.text_color)

        self.screen.blit(temp, (60, 170))
        self.screen.blit(hum, (60, 220))
        self.screen.blit(co2, (60, 270))

    def _draw_counts_card(self, counts: MoodCounts, pending_counts: MoodCounts | None = None) -> None:
        rect = pygame.Rect(40, 370, 430, 180)
        self._draw_card(rect)

        title = self.label_font.render("Heutige Stimmungs-Zähler", True, self.text_color)
        self.screen.blit(title, (60, 395))

        pending_counts = pending_counts or MoodCounts()
        good = self.value_font.render(f"Gut: {self._format_count(counts.good, pending_counts.good)}", True, self.ok_color)
        neutral = self.value_font.render(f"Neutral: {self._format_count(counts.neutral, pending_counts.neutral)}", True, self.warn_color)
        bad = self.value_font.render(f"Schlecht: {self._format_count(counts.bad, pending_counts.bad)}", True, self.err_color)

        self.screen.blit(good, (60, 445))
        self.screen.blit(neutral, (60, 490))
        self.screen.blit(bad, (250, 445))

    def _draw_smiley_card(self, status: str) -> None:
        rect = pygame.Rect(520, 90, 460, 460)
        self._draw_card(rect)

        title = self.label_font.render("Raum-Stimmung", True, self.text_color)
        self.screen.blit(title, (540, 115))

        smiley = self.smileys[status]
        smiley_x = 520 + (460 - smiley.get_width()) // 2
        self.screen.blit(smiley, (smiley_x, 170))

        label_text = _MOOD_LABELS.get(status, status.upper())
        label = self.title_font.render(label_text, True, self.text_color)
        label_x = 520 + (460 - label.get_width()) // 2
        self.screen.blit(label, (label_x, 420))

    def _draw_status_bar(self, server_connected: bool, last_upload_status: str) -> None:
        bar_y = self.height - 34
        pygame.draw.rect(self.screen, self.border_color, pygame.Rect(0, bar_y, self.width, 34))

        conn_color = self.ok_color if server_connected else self.err_color
        conn_text = "Server: verbunden" if server_connected else "Server: offline"

        parts = [
            (f"Gerät: {self.device_id}", self.subtle_color),
            (conn_text, conn_color),
            (f"Letzter Upload: {last_upload_status}", self.subtle_color),
            ("[U] Upload  [R] Aktualisieren  [ESC] Beenden", self.subtle_color),
        ]

        x = 16
        for text, color in parts:
            surf = self.status_font.render(text, True, color)
            self.screen.blit(surf, (x, bar_y + 8))
            x += surf.get_width() + 40

    def _draw_card(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, self.card_color, rect, border_radius=18)
        pygame.draw.rect(self.screen, self.border_color, rect, width=2, border_radius=18)

    @staticmethod
    def _format_count(value: int, pending_delta: int) -> str:
        return f"{value}*" if pending_delta > 0 else str(value)
