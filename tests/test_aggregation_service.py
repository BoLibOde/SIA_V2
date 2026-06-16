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


# --- build_window_payload tests (manual / U-key upload) ---

def test_build_window_payload_aggregates_arbitrary_window() -> None:
    service = AggregationService()
    period_start = datetime(2024, 1, 1, 10, 0, 0)
    period_end = datetime(2024, 1, 1, 11, 30, 0)
    samples = [
        SensorReading(temperature_c=20.0, humidity_pct=40.0, co2_ppm=600, timestamp=datetime(2024, 1, 1, 10, 15, 0)),
        SensorReading(temperature_c=22.0, humidity_pct=44.0, co2_ppm=650, timestamp=datetime(2024, 1, 1, 11, 15, 0)),
    ]

    payload = service.build_window_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(good=5, neutral=1, bad=2),
        sensor_samples=samples,
        period_start=period_start,
        period_end=period_end,
    )

    assert payload is not None
    assert payload.period_start == period_start
    assert payload.period_end == period_end
    assert payload.mood_counts.good == 5
    assert payload.mood_counts.bad == 2
    assert payload.sensor_avg_temperature_c == 21.0
    assert payload.sample_count == 2


def test_build_window_payload_returns_none_without_samples_in_window() -> None:
    service = AggregationService()
    period_start = datetime(2024, 1, 1, 12, 0, 0)
    period_end = datetime(2024, 1, 1, 13, 0, 0)
    # Samples outside the window
    samples = [
        SensorReading(temperature_c=21.0, humidity_pct=41.0, co2_ppm=610, timestamp=datetime(2024, 1, 1, 10, 0, 0)),
    ]

    payload = service.build_window_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(good=1, neutral=0, bad=0),
        sensor_samples=samples,
        period_start=period_start,
        period_end=period_end,
    )

    assert payload is None


def test_build_window_payload_excludes_sample_at_period_end() -> None:
    """Sample exactly at period_end should not be included (half-open interval)."""
    service = AggregationService()
    period_start = datetime(2024, 1, 1, 10, 0, 0)
    period_end = datetime(2024, 1, 1, 11, 0, 0)
    samples = [
        SensorReading(temperature_c=21.0, humidity_pct=41.0, co2_ppm=610, timestamp=datetime(2024, 1, 1, 10, 30, 0)),
        SensorReading(temperature_c=25.0, humidity_pct=50.0, co2_ppm=700, timestamp=period_end),  # excluded
    ]

    payload = service.build_window_payload(
        device_id='pi-room-01',
        mood_counts=MoodCounts(),
        sensor_samples=samples,
        period_start=period_start,
        period_end=period_end,
    )

    assert payload is not None
    assert payload.sample_count == 1
    assert payload.sensor_avg_temperature_c == 21.0
