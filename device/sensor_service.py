import random
import threading
import time
from datetime import datetime
from typing import Optional

from device.models import SensorReading


class SensorService:
    def __init__(self, read_interval_seconds: int = 5) -> None:
        self.read_interval_seconds = read_interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_reading: Optional[SensorReading] = None
        self.readings: list[SensorReading] = []

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1)

    def get_latest_reading(self) -> Optional[SensorReading]:
        return self.latest_reading

    def get_hour_samples(self) -> list[SensorReading]:
        return list(self.readings)

    def _loop(self) -> None:
        while self.running:
            reading = self._read_sensor()
            self.latest_reading = reading
            self.readings.append(reading)

            if len(self.readings) > 720:
                self.readings.pop(0)

            time.sleep(self.read_interval_seconds)

    def _read_sensor(self) -> SensorReading:
        temperature_c = round(22 + random.uniform(-1.5, 1.5), 2)
        humidity_pct = round(45 + random.uniform(-5, 5), 2)
        co2_ppm = int(500 + random.uniform(-60, 120))

        return SensorReading(
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            co2_ppm=co2_ppm,
            timestamp=datetime.utcnow(),
        )
