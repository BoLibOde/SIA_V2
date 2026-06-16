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


def test_upload_live_event_sends_mood_counts_and_sensor(tmp_path) -> None:
    service = _make_service(tmp_path)
    reading = _build_reading()
    ts = datetime(2024, 1, 1, 9, 30, 0)
    response = Mock(status_code=201)

    with patch("device.upload_service.requests.post", return_value=response) as post_mock:
        ok, status = service.upload_live_event("good", reading, ts)

    assert ok is True
    assert status == "live-ok"
    body = post_mock.call_args.kwargs["json"]
    assert body["mood_counts"] == {"good": 1, "neutral": 0, "bad": 0}
    assert body["sensor_avg"]["co2_ppm"] == 615
    assert body["created_at"] == ts.isoformat()


def test_upload_live_event_returns_false_on_connection_error(tmp_path) -> None:
    import requests as req_mod

    service = _make_service(tmp_path)
    reading = _build_reading()

    with patch("device.upload_service.requests.post", side_effect=req_mod.ConnectionError()):
        ok, status = service.upload_live_event("bad", reading, datetime(2024, 1, 1, 9, 0, 0))

    assert ok is False
    assert "connection-error" in status


def test_upload_live_event_treats_409_as_success(tmp_path) -> None:
    service = _make_service(tmp_path)
    reading = _build_reading()

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=409)):
        ok, status = service.upload_live_event("neutral", reading, datetime(2024, 1, 1, 9, 0, 0))

    assert ok is True
    assert status == "live-duplicate"


def test_save_failed_dict_appends_to_retry_file(tmp_path) -> None:
    service = _make_service(tmp_path)
    body = {"mood_counts": {"good": 1, "neutral": 0, "bad": 0}, "created_at": "2024-01-01T09:30:00"}
    service.save_failed_dict(body)

    pending = service._read_pending()
    assert len(pending) == 1
    assert pending[0]["mood_counts"]["good"] == 1


def test_save_failed_dict_and_retry_pending_together(tmp_path) -> None:
    """Failed live events stored via save_failed_dict are retried by retry_pending_uploads."""
    service = _make_service(tmp_path)
    body = {
        "mood_counts": {"good": 0, "neutral": 0, "bad": 1},
        "sensor_avg": {"temperature_c": 20.0, "humidity_pct": 40.0, "co2_ppm": 600},
        "created_at": "2024-01-01T09:00:00",
    }
    service.save_failed_dict(body)

    assert len(service._read_pending()) == 1

    with patch("device.upload_service.requests.post", return_value=Mock(status_code=201)):
        service.retry_pending_uploads()

    # Successfully retried entries are removed from the file
    assert len(service._read_pending()) == 0
