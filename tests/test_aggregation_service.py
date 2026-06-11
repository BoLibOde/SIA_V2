from datetime import datetime

from device.aggregation_service import AggregationService
from device.models import MoodCounts, SensorReading


def test_build_hourly_payload_calculates_averages() -> None:
    service = AggregationService()
    now = datetime(2024, 1, 1, 10, 30, 0)
    samples = [
        SensorReading(temperature_c=20.0, humidity_pct=40.0, co2_ppm=500, timestamp=datetime(2024, 1, 1, 9, 5, 0)),
        SensorReading(temperature_c=22.0, humidity_pct=44.0, co2_ppm=700, timestamp=datetime(2024, 1, 1, 9, 45, 0)),
    ]

    payload = service.build_hourly_payload(
        device_id="device-1",
        mood_counts=MoodCounts(good=3, neutral=2, bad=1),
        sensor_samples=samples,
        now=now,
    )

    assert payload is not None
    assert payload.sensor_avg_temperature_c == 21.0
    assert payload.sensor_avg_humidity_pct == 42.0
    assert payload.sensor_avg_co2_ppm == 600
    assert payload.sample_count == 2


def test_build_hourly_payload_returns_none_without_samples() -> None:
    service = AggregationService()

    payload = service.build_hourly_payload(
        device_id="device-1",
        mood_counts=MoodCounts(),
        sensor_samples=[],
        now=datetime(2024, 1, 1, 10, 0, 0),
    )

    assert payload is None


def test_build_hourly_payload_ignores_samples_outside_target_hour() -> None:
    service = AggregationService()
    now = datetime(2024, 1, 1, 10, 30, 0)
    samples = [
        SensorReading(temperature_c=19.0, humidity_pct=39.0, co2_ppm=450, timestamp=datetime(2024, 1, 1, 8, 59, 59)),
        SensorReading(temperature_c=21.0, humidity_pct=41.0, co2_ppm=550, timestamp=datetime(2024, 1, 1, 9, 15, 0)),
        SensorReading(temperature_c=23.0, humidity_pct=43.0, co2_ppm=650, timestamp=datetime(2024, 1, 1, 10, 0, 0)),
    ]

    payload = service.build_hourly_payload(
        device_id="device-1",
        mood_counts=MoodCounts(good=1),
        sensor_samples=samples,
        now=now,
    )

    assert payload is not None
    assert payload.sensor_avg_temperature_c == 21.0
    assert payload.sensor_avg_humidity_pct == 41.0
    assert payload.sensor_avg_co2_ppm == 550
    assert payload.sample_count == 1
