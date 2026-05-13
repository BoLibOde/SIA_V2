from dataclasses import dataclass
from datetime import datetime


@dataclass
class SensorReading:
    temperature_c: float
    humidity_pct: float
    co2_ppm: int
    timestamp: datetime


@dataclass
class MoodCounts:
    good: int = 0
    neutral: int = 0
    bad: int = 0

    def total(self) -> int:
        return self.good + self.neutral + self.bad


@dataclass
class HourlyUploadPayload:
    device_id: str
    period_start: datetime
    period_end: datetime
    mood_counts: MoodCounts
    sensor_avg_temperature_c: float
    sensor_avg_humidity_pct: float
    sensor_avg_co2_ppm: int
    sample_count: int
