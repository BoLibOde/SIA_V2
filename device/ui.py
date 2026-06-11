from pathlib import Path

import pygame

from device.gpio_handler import MoodCounts
from device.models import SensorReading


class DeviceUI:
    def __init__(self, width: int, height: int, fullscreen: bool = True, device_id: str = "") -> None:
        pygame.init()
        pygame.font.init()

        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("SIA V2")

        self.width = width
        self.height = height
        self.device_id = device_id

        self.bg_color = (245, 247, 250)
        self.card_color = (255, 255, 255)
        self.border_color = (220, 225, 232)
        self.text_color = (30, 35, 40)
        self.subtle_color = (100, 110, 120)
        self.ok_color = (50, 145, 80)
        self.err_color = (180, 60, 60)

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

    def _load_smiley(self, path: Path) -> pygame.Surface:
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, (220, 220))

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def draw(
        self,
        reading: SensorReading | None,
        counts: MoodCounts,
        server_connected: bool = False,
        last_upload_status: str = "—",
    ) -> None:
        status = self._pick_status(counts)

        self.screen.fill(self.bg_color)
        self._draw_title()
        self._draw_sensor_card(reading)
        self._draw_counts_card(counts)
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
        title = self.title_font.render("SIA V2 Mood Bar-o-meter", True, self.text_color)
        self.screen.blit(title, (40, 25))

    def _draw_sensor_card(self, reading: SensorReading | None) -> None:
        rect = pygame.Rect(40, 90, 430, 250)
        self._draw_card(rect)

        title = self.label_font.render("Live Sensor Values", True, self.text_color)
        self.screen.blit(title, (60, 115))

        if reading is None:
            text = self.value_font.render("No sensor data yet", True, self.subtle_color)
            self.screen.blit(text, (60, 190))
            return

        temp = self.value_font.render(f"Temperature: {reading.temperature_c:.1f} C", True, self.text_color)
        hum = self.value_font.render(f"Humidity: {reading.humidity_pct:.1f} %", True, self.text_color)
        co2 = self.value_font.render(f"CO2: {reading.co2_ppm} ppm", True, self.text_color)

        self.screen.blit(temp, (60, 170))
        self.screen.blit(hum, (60, 220))
        self.screen.blit(co2, (60, 270))

    def _draw_counts_card(self, counts: MoodCounts) -> None:
        rect = pygame.Rect(40, 370, 430, 180)
        self._draw_card(rect)

        title = self.label_font.render("Current Hour Mood Counts", True, self.text_color)
        self.screen.blit(title, (60, 395))

        good = self.value_font.render(f"Good: {counts.good}", True, self.ok_color)
        neutral = self.value_font.render(f"Neutral: {counts.neutral}", True, (180, 140, 40))
        bad = self.value_font.render(f"Bad: {counts.bad}", True, self.err_color)

        self.screen.blit(good, (60, 445))
        self.screen.blit(neutral, (60, 490))
        self.screen.blit(bad, (250, 445))

    def _draw_smiley_card(self, status: str) -> None:
        rect = pygame.Rect(520, 90, 460, 460)
        self._draw_card(rect)

        title = self.label_font.render("Room Mood", True, self.text_color)
        self.screen.blit(title, (540, 115))

        smiley = self.smileys[status]
        smiley_x = 520 + (460 - smiley.get_width()) // 2
        self.screen.blit(smiley, (smiley_x, 170))

        label = self.title_font.render(status.upper(), True, self.text_color)
        label_x = 520 + (460 - label.get_width()) // 2
        self.screen.blit(label, (label_x, 420))

    def _draw_status_bar(self, server_connected: bool, last_upload_status: str) -> None:
        bar_y = self.height - 34
        pygame.draw.rect(self.screen, self.border_color, pygame.Rect(0, bar_y, self.width, 34))

        conn_color = self.ok_color if server_connected else self.err_color
        conn_text = "Server: connected" if server_connected else "Server: offline"

        parts = [
            (f"Device: {self.device_id}", self.subtle_color),
            (conn_text, conn_color),
            (f"Last upload: {last_upload_status}", self.subtle_color),
        ]

        x = 16
        for text, color in parts:
            surf = self.status_font.render(text, True, color)
            self.screen.blit(surf, (x, bar_y + 8))
            x += surf.get_width() + 40

    def _draw_card(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, self.card_color, rect, border_radius=18)
        pygame.draw.rect(self.screen, self.border_color, rect, width=2, border_radius=18)

