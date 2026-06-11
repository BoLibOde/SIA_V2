import json
from pathlib import Path

import requests

from device.models import HourlyUploadPayload


class UploadService:
    def __init__(
        self,
        server_base_url: str,
        upload_endpoint: str,
        health_endpoint: str = "/api/v1/health",
        retry_file: str = "device/pending_uploads.json",
        timeout_seconds: int = 10,
    ) -> None:
        self.server_base_url = server_base_url.rstrip("/")
        self.upload_endpoint = upload_endpoint
        self.health_endpoint = health_endpoint
        self.timeout = timeout_seconds
        self.retry_file = Path(retry_file)
        self.retry_file.parent.mkdir(parents=True, exist_ok=True)

    def check_server_health(self) -> bool:
        """Returns True if the server responds to the health endpoint."""
        try:
            url = f"{self.server_base_url}{self.health_endpoint}"
            resp = requests.get(url, timeout=self.timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def upload_hourly_payload(self, payload: HourlyUploadPayload) -> tuple[bool, str]:
        """Upload one hourly payload. Returns (success, status_message)."""
        url = f"{self.server_base_url}{self.upload_endpoint}"
        body = self._payload_to_dict(payload)
        try:
            resp = requests.post(url, json=body, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return True, "ok"
            if resp.status_code == 409:
                # Already stored – treat as success so we don't retry endlessly
                return True, "duplicate"
            return False, f"http-{resp.status_code}"
        except requests.ConnectionError:
            return False, "connection-error"
        except requests.Timeout:
            return False, "timeout"
        except requests.RequestException as exc:
            return False, str(exc)

    def retry_pending_uploads(self) -> None:
        pending = self._read_pending()
        if not pending:
            return

        still_pending = []
        for body in pending:
            try:
                resp = requests.post(
                    f"{self.server_base_url}{self.upload_endpoint}",
                    json=body,
                    timeout=self.timeout,
                )
                if resp.status_code not in (200, 201, 409):
                    still_pending.append(body)
            except requests.RequestException:
                still_pending.append(body)

        self._write_pending(still_pending)

    def save_failed_upload(self, payload: HourlyUploadPayload) -> None:
        pending = self._read_pending()
        pending.append(self._payload_to_dict(payload))
        self._write_pending(pending)

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

    def _read_pending(self) -> list[dict]:
        if not self.retry_file.exists():
            return []
        try:
            return json.loads(self.retry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write_pending(self, payloads: list[dict]) -> None:
        self.retry_file.write_text(json.dumps(payloads, indent=2), encoding="utf-8")

