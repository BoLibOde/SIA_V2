from datetime import datetime
from unittest.mock import Mock, patch

from device.models import HourlyUploadPayload, MoodCounts
from device.upload_service import UploadService


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
