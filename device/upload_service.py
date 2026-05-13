import json
from pathlib import Path

import requests

from device.models import HourlyUploadPayload


class UploadService:
    def __init__(self, server_base_url: str, upload_endpoint: str, retry_file: str = "device/pending_uploads.json") -> None:
        self.server_base_url = server_base_url.rstrip("/")
        self.upload_endpoint = upload_endpoint
        self.retry_file = Path(retry_file)
        self.retry_file.parent.mkdir(parents=True, exist_ok=True)

    def upload_hourly_payload(self, payload: HourlyUploadPayload) -> bool:
        url = f"{self.server_base_url}{self.upload_endpoint}"
        request_body = self._payload_to_dict(payload)

        try:
            response = requests.post(url, json=request_body, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def retry_pending_uploads(self) -> None:
        pending = self._read_pending_uploads()
        if not pending:
            return

        still_pending = []
        for payload in pending:
            try:
                response = requests.post(
                    f"{self.server_base_url}{self.upload_endpoint}",
                    json=payload,
                    timeout=10,
                )
                if response.status_code != 200:
                    still_pending.append(payload)
            except requests.RequestException:
                still_pending.append(payload)

        self._write_pending_uploads(still_pending)

    def save_failed_upload(self, payload: HourlyUploadPayload) -> None:
        pending = self._read_pending_uploads()
        pending.append(self._payload_to_dict(payload))
        self._write_pending_uploads(pending)

    def _payload_to_dict(self, payload: HourlyUploadPayload) -> dict:
        return {
            "device_id": payload.device_id,
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
            "mood_counts": {
                "good": payload.mood_counts.good,
                "neutral": payload.mood_counts.neutral,
                "bad": payload.mood_counts.bad,
            },
            "sensor_avg": {
                "temperature_c": payload.sensor_avg_temperature_c,
                "humidity_pct": payload.sensor_avg_humidity_pct,
                "co2_ppm": payload.sensor_avg_co2_ppm,
            },
            "sample_count": payload.sample_count,
        }

    def _read_pending_uploads(self) -> list[dict]:
        if not self.retry_file.exists():
            return []

        try:
            return json.loads(self.retry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write_pending_uploads(self, payloads: list[dict]) -> None:
        self.retry_file.write_text(json.dumps(payloads, indent=2), encoding="utf-8")
