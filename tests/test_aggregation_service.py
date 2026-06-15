from datetime import datetime

from device.aggregation_service import AggregationService
from device.models import MoodCounts, SensorReading


def test_build_hourly_payload_calculates_average_values() -> None:
    service = AggregationService()
    now = datetime(2024, 1, 1, 10, 0, 0)
    samples = [
        SensorReading(temperature_c=20.0, humidity_pct=40.0, co2_ppm=600, timestamp=datetime(2024, 1, 1, 9, 10, 0)),
        SensorReading(temperature_c=22.0, humidity_pct=44.0, co2_ppm=650, timestamp=datetime(2024, 1, 1, 9, 40, 0)),
    ]

    payload = service.build_hourly_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(good=3, neutral=2, bad=1),
        sensor_samples=samples,
        now=now,
    )

    assert payload is not None
    assert payload.period_start == datetime(2024, 1, 1, 9, 0, 0)
    assert payload.period_end == datetime(2024, 1, 1, 10, 0, 0)
    assert payload.sensor_avg_temperature_c == 21.0
    assert payload.sensor_avg_humidity_pct == 42.0
    assert payload.sensor_avg_co2_ppm == 625
    assert payload.sample_count == 2


def test_build_hourly_payload_returns_none_without_samples() -> None:
    service = AggregationService()

    payload = service.build_hourly_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(),
        sensor_samples=[],
        now=datetime(2024, 1, 1, 10, 0, 0),
    )

    assert payload is None


def test_build_hourly_payload_ignores_samples_outside_target_hour() -> None:
    service = AggregationService()
    now = datetime(2024, 1, 1, 10, 0, 0)
    samples = [
        SensorReading(temperature_c=19.0, humidity_pct=38.0, co2_ppm=590, timestamp=datetime(2024, 1, 1, 8, 59, 59)),
        SensorReading(temperature_c=21.0, humidity_pct=41.0, co2_ppm=610, timestamp=datetime(2024, 1, 1, 9, 30, 0)),
        SensorReading(temperature_c=23.0, humidity_pct=45.0, co2_ppm=700, timestamp=datetime(2024, 1, 1, 10, 0, 0)),
    ]

    payload = service.build_hourly_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(good=1, neutral=0, bad=0),
        sensor_samples=samples,
        now=now,
    )

    assert payload is not None
    assert payload.sensor_avg_temperature_c == 21.0
    assert payload.sensor_avg_humidity_pct == 41.0
    assert payload.sensor_avg_co2_ppm == 610
    assert payload.sample_count == 1
