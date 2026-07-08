import time
from pathlib import Path

import pygame

from device.gpio_handler import MoodCounts
from device.models import SensorReading

# German labels for mood status displayed in the smiley card
_MOOD_LABELS = {"good": "GUT", "neutral": "NEUTRAL", "bad": "SCHLECHT"}

# Status-bar rotation: interval between steps (seconds) and total number of steps
_STATUS_ROTATION_INTERVAL_S: float = 3.5
_STATUS_ROTATION_STEPS: int = 3


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
        self.status_font = pygame.font.SysFont("arial", 15)

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

        # Epoch used to drive the synchronised status-bar rotation.
        self._rotation_epoch: float = time.monotonic()

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
        counts: MoodCounts | None,
        pending_counts: MoodCounts | None = None,
        server_connected: bool = False,
        last_upload_status: str = "—",
        operating_mode: str = "online",
        sensor_status_text: str = "FEHLER",
        sensor_has_data: bool = False,
        sensor_hardware_active: bool = False,
    ) -> None:
        status = self._pick_status(counts)

        self.screen.fill(self.bg_color)
        self._draw_title()
        self._draw_sensor_card(reading)
        self._draw_counts_card(counts, pending_counts, operating_mode)
        self._draw_smiley_card(status)
        self._draw_status_bar(
            reading,
            server_connected,
            last_upload_status,
            operating_mode,
            sensor_status_text,
            sensor_has_data,
            sensor_hardware_active,
        )
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()

    def _pick_status(self, counts: MoodCounts | None) -> str:
        if counts is None:
            return "neutral"
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

    def _draw_counts_card(self, counts: MoodCounts | None, pending_counts: MoodCounts | None = None, operating_mode: str = "online") -> None:
        rect = pygame.Rect(40, 370, 430, 180)
        self._draw_card(rect)

        title = self.label_font.render("Heutige Stimmungs-Zähler", True, self.text_color)
        self.screen.blit(title, (60, 395))

        pending_counts = pending_counts or MoodCounts()
        good_value = None if counts is None else counts.good
        neutral_value = None if counts is None else counts.neutral
        bad_value = None if counts is None else counts.bad
        good = self.value_font.render(f"Gut: {self._format_count(good_value, pending_counts.good, operating_mode)}", True, self.ok_color)
        neutral = self.value_font.render(f"Neutral: {self._format_count(neutral_value, pending_counts.neutral, operating_mode)}", True, self.warn_color)
        bad = self.value_font.render(f"Schlecht: {self._format_count(bad_value, pending_counts.bad, operating_mode)}", True, self.err_color)

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

    def _draw_status_bar(
        self,
        reading: SensorReading | None,
        server_connected: bool,
        last_upload_status: str,
        operating_mode: str = "online",
        sensor_status_text: str = "FEHLER",
        sensor_has_data: bool = False,
        sensor_hardware_active: bool = False,
    ) -> None:
        bar_y = self.height - 34
        pygame.draw.rect(self.screen, self.border_color, pygame.Rect(0, bar_y, self.width, 34))

        # Determine current rotation step (0, 1, or 2) from elapsed time
        elapsed = time.monotonic() - self._rotation_epoch
        step = int(elapsed / _STATUS_ROTATION_INTERVAL_S) % _STATUS_ROTATION_STEPS

        # --- Left-side info panels ---
        if operating_mode == "offline":
            mode_text = "Modus: Offline (Lokal)"
            mode_color = self.warn_color
        else:
            mode_text = f"Modus: Online | Server: {'verbunden' if server_connected else 'offline (lokal gepuffert)'}"
            mode_color = self.ok_color if server_connected else self.err_color

        if sensor_status_text != "OK" or not sensor_has_data or reading is None:
            sensor_text = "Sensoren: ⚠ Fehler"
            sensor_color = self.err_color
        else:
            sensor_text = f"Sensoren: OK | CO2: {reading.co2_ppm} ppm"
            sensor_color = self.ok_color

        left_panels = [
            (mode_text, mode_color),
            (sensor_text, sensor_color),
            (f"Letzter Upload: {last_upload_status}", self.subtle_color),
        ]

        # --- Right-side keyboard-hint panels (synchronised with left) ---
        right_panels = [
            ("[U] Upload  [R] Reset", self.subtle_color),
            ("[ESC] Beenden", self.subtle_color),
            ("[U] Upload  [R] Reset", self.subtle_color),
        ]

        left_text, left_color = left_panels[step]
        right_text, right_color = right_panels[step]

        left_surf = self.status_font.render(left_text, True, left_color)
        right_surf = self.status_font.render(right_text, True, right_color)

        text_y = bar_y + (34 - left_surf.get_height()) // 2
        self.screen.blit(left_surf, (16, text_y))
        self.screen.blit(right_surf, (self.width - right_surf.get_width() - 16, text_y))

    def _draw_card(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, self.card_color, rect, border_radius=18)
        pygame.draw.rect(self.screen, self.border_color, rect, width=2, border_radius=18)

    @staticmethod
    def _format_count(value: int | None, pending_delta: int, operating_mode: str = "online") -> str:
        if value is None:
            return "--"
        if pending_delta > 0 and operating_mode != "offline":
            return f"{value}*"
        return str(value)
