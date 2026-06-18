from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from device.models import HourlyUploadPayload, MoodCounts, SensorReading
from device.upload_service import UploadService


def _make_service(tmp_path, token: str = "secret-token") -> UploadService:
    return UploadService(
        server_base_url="http://example.local",
        upload_endpoint="/device_ingest.php",
        health_endpoint="/device_ingest.php",
        device_token=token,
        retry_file=str(tmp_path / "pending.json"),
    )


def _build_payload() -> HourlyUploadPayload:
    return HourlyUploadPayload(
        device_id="pi-room-01",
        period_start=datetime(2024, 1, 1, 9, 0, 0),
        period_end=datetime(2024, 1, 1, 10, 0, 0),
        mood_counts=MoodCounts(good=2, neutral=1, bad=0),
        sensor_avg_temperature_c=21.5,
        sensor_avg_humidity_pct=41.0,
        sensor_avg_co2_ppm=615,
        sample_count=12,
    )


def _build_reading() -> SensorReading:
    return SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0),
    )


def test_upload_hourly_payload_sends_device_token_header() -> None:
    service = UploadService(
        server_base_url="http://example.local",
        upload_endpoint="/device_ingest.php",
        health_endpoint="/device_ingest.php",
        device_token="secret-token",
    )
    payload = _build_payload()
    response = Mock(status_code=201)

    with patch("device.upload_service.requests.post", return_value=response) as post_mock:
        success, status = service.upload_hourly_payload(payload)

    assert success is True
    assert status == "ok"
    post_mock.assert_called_once()
    assert post_mock.call_args.kwargs["headers"]["X-Device-Token"] == "secret-token"


def test_check_server_health_uses_get_with_headers() -> None:
    service = UploadService(
        server_base_url="http://example.local",
        upload_endpoint="/device_ingest.php",
        health_endpoint="/device_ingest.php",
        device_token="secret-token",
    )
    response = Mock(status_code=200)

    with patch("device.upload_service.requests.get", return_value=response) as get_mock:
        ok = service.check_server_health()

    assert ok is True
    get_mock.assert_called_once()
    assert get_mock.call_args.kwargs["headers"]["X-Device-Token"] == "secret-token"


def test_fetch_today_counts_sends_device_id_and_parses_counts(tmp_path) -> None:
    service = _make_service(tmp_path)
    response = Mock(
        status_code=200,
        json=Mock(
            return_value={
                "status": "ok",
                "date": "2026-06-18",
                "counts": {"good": 12, "neutral": 4, "bad": 3},
            }
        ),
    )

    with patch("device.upload_service.requests.get", return_value=response) as get_mock:
        ok, counts, counts_date, status = service.fetch_today_counts("pi-room-01")

    assert ok is True
    assert counts is not None
    assert counts.good == 12
    assert counts.neutral == 4
    assert counts.bad == 3
    assert counts_date == "2026-06-18"
    assert status == "today-ok"
    assert get_mock.call_args.kwargs["params"]["device_id"] == "pi-room-01"
    assert get_mock.call_args.kwargs["headers"]["X-Device-Token"] == "secret-token"


def test_fetch_today_counts_returns_error_on_invalid_payload(tmp_path) -> None:
    service = _make_service(tmp_path)
    response = Mock(status_code=200, json=Mock(return_value={"status": "ok"}))

    with patch("device.upload_service.requests.get", return_value=response):
        ok, counts, counts_date, status = service.fetch_today_counts("pi-room-01")

    assert ok is False
    assert counts is None
    assert counts_date == ""
    assert status == "today-invalid-payload"


def test_upload_live_event_sends_direct_measurement_payload(tmp_path) -> None:
    service = _make_service(tmp_path)
    reading = _build_reading()
    ts = datetime(2024, 1, 1, 9, 30, 0)
    response = Mock(status_code=201)

    with patch("device.upload_service.requests.post", return_value=response) as post_mock:
        ok, status = service.upload_live_event("good", reading, ts)

    assert ok is True
    assert status == "live-ok"
    body = post_mock.call_args.kwargs["json"]
    assert body["upload_type"] == "mood_live"
    assert body["mood"] == "positiv"
    assert body["co2"] == 615
    assert body["humidity"] == 41.0
    assert body["temperature"] == 21.5
    assert body["created_at"] == ts.isoformat()


def test_upload_live_event_returns_false_on_connection_error(tmp_path) -> None:
    import requests as req_mod

    service = _make_service(tmp_path)
    reading = _build_reading()

    with patch("device.upload_service.requests.post", side_effect=req_mod.ConnectionError()):
        ok, status = service.upload_live_event("bad", reading, datetime(2024, 1, 1, 9, 0, 0))

    assert ok is False
    assert "connection-error" in status
    # Failed live event must have been persisted automatically
    assert len(service._read_pending()) == 1


def test_upload_live_event_treats_409_as_success(tmp_path) -> None:
    service = _make_service(tmp_path)
    reading = _build_reading()

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=409)):
        ok, status = service.upload_live_event("neutral", reading, datetime(2024, 1, 1, 9, 0, 0))

    assert ok is True
    assert status == "live-duplicate"


def test_save_failed_dict_appends_to_retry_file(tmp_path) -> None:
    service = _make_service(tmp_path)
    body = {"upload_type": "mood_live", "mood": "positiv", "co2": 615, "humidity": 41.0, "temperature": 21.5, "created_at": "2024-01-01T09:30:00"}
    service.save_failed_dict(body)

    pending = service._read_pending()
    assert len(pending) == 1
    assert pending[0]["mood"] == "positiv"


def test_save_failed_dict_and_retry_pending_together(tmp_path) -> None:
    """Failed live events stored via save_failed_dict are retried by retry_pending_uploads."""
    service = _make_service(tmp_path)
    body = {
        "upload_type": "mood_live",
        "mood": "negativ",
        "temperature": 20.0,
        "humidity": 40.0,
        "co2": 600,
        "created_at": "2024-01-01T09:00:00",
    }
    service.save_failed_dict(body)

    assert len(service._read_pending()) == 1

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=201)):
        sent_count, remaining_count = service.retry_pending_uploads()

    # Successfully retried entries are removed from the file
    assert sent_count == 1
    assert remaining_count == 0
    assert len(service._read_pending()) == 0


def test_save_failed_upload_deduplicates_identical_hourly_payload(tmp_path) -> None:
    """save_failed_upload must not append a duplicate when the same hourly window is already queued."""
    service = _make_service(tmp_path)
    payload = _build_payload()

    service.save_failed_upload(payload)
    service.save_failed_upload(payload)  # second call with identical payload

    pending = service._read_pending()
    assert len(pending) == 1, "duplicate hourly aggregate must not be added twice"


def test_save_failed_upload_keeps_different_periods(tmp_path) -> None:
    """Two payloads with different period_start values are both queued."""
    from datetime import datetime

    service = _make_service(tmp_path)
    payload_a = HourlyUploadPayload(
        device_id="pi-room-01",
        period_start=datetime(2024, 1, 1, 9, 0, 0),
        period_end=datetime(2024, 1, 1, 10, 0, 0),
        mood_counts=MoodCounts(good=1, neutral=0, bad=0),
        sensor_avg_temperature_c=21.0,
        sensor_avg_humidity_pct=40.0,
        sensor_avg_co2_ppm=600,
        sample_count=10,
    )
    payload_b = HourlyUploadPayload(
        device_id="pi-room-01",
        period_start=datetime(2024, 1, 1, 10, 0, 0),
        period_end=datetime(2024, 1, 1, 11, 0, 0),
        mood_counts=MoodCounts(good=0, neutral=1, bad=0),
        sensor_avg_temperature_c=22.0,
        sensor_avg_humidity_pct=41.0,
        sensor_avg_co2_ppm=620,
        sample_count=12,
    )

    service.save_failed_upload(payload_a)
    service.save_failed_upload(payload_b)

    pending = service._read_pending()
    assert len(pending) == 2


def test_retry_pending_uploads_deduplicates_before_sending(tmp_path) -> None:
    """retry_pending_uploads collapses duplicate hourly aggregate entries so only one is sent."""
    service = _make_service(tmp_path)
    payload = _build_payload()
    # Manually write 44 identical entries (simulates historical bug)
    duplicate_entry = service._payload_to_dict(payload)
    service._write_pending([duplicate_entry] * 44)

    assert len(service._read_pending()) == 44

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=201)):
        sent_count, remaining_count = service.retry_pending_uploads()

    assert sent_count == 1
    assert remaining_count == 0
    assert len(service._read_pending()) == 0


def test_retry_pending_uploads_preserves_live_events_during_dedup(tmp_path) -> None:
    """Live-event entries (no period_start) are never dropped by deduplication."""
    service = _make_service(tmp_path)
    live_a = {"upload_type": "mood_live", "mood": "positiv", "co2": 600, "humidity": 40.0, "temperature": 20.0, "created_at": "2024-01-01T09:30:00"}
    live_b = {"upload_type": "mood_live", "mood": "neutral", "co2": 605, "humidity": 41.0, "temperature": 20.5, "created_at": "2024-01-01T09:31:00"}
    service._write_pending([live_a, live_b])

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=201)):
        sent_count, remaining_count = service.retry_pending_uploads()

    assert sent_count == 2
    assert remaining_count == 0


def test_retry_pending_uploads_reports_successes_and_remaining_failures(tmp_path) -> None:
    service = _make_service(tmp_path)
    service.save_failed_dict({"upload_type": "mood_live", "created_at": "2024-01-01T09:00:00", "mood": "neutral", "co2": 600, "humidity": 40, "temperature": 21})
    service.save_failed_dict({"upload_type": "mood_live", "created_at": "2024-01-01T09:01:00", "mood": "negativ", "co2": 610, "humidity": 41, "temperature": 22})

    responses = [Mock(status_code=201), Mock(status_code=500)]
    with patch("device.upload_service.requests.post", side_effect=responses):
        sent_count, remaining_count = service.retry_pending_uploads()

    assert sent_count == 1
    assert remaining_count == 1
    pending = service._read_pending()
    assert len(pending) == 1
    assert pending[0]["mood"] == "negativ"


def test_upload_hourly_payload_sends_sensor_only_hourly_format(tmp_path) -> None:
    service = _make_service(tmp_path)
    payload = _build_payload()

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=201)) as post_mock:
        ok, status = service.upload_hourly_payload(payload)

    assert ok is True
    assert status == "ok"
    body = post_mock.call_args.kwargs["json"]
    assert body["upload_type"] == "sensor_hourly"
    assert body["device_id"] == "pi-room-01"
    assert body["period_start"] == payload.period_start.isoformat()
    assert body["period_end"] == payload.period_end.isoformat()
    assert body["sensor_avg"]["co2_ppm"] == 615
    assert "mood_counts" not in body
