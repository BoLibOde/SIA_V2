import json
from datetime import datetime
from pathlib import Path

import requests

from device.models import HourlyUploadPayload, SensorReading


class UploadService:
    """Handles all three upload tracks for the Raspberry Pi device.

    Upload tracks
    -------------
    1. **Hourly aggregate** – ``upload_hourly_payload()`` sends a full
       60-minute aggregate (mood counts + sensor averages).  Called by
       ``_try_hourly_upload()`` in main.py and also used for manual aggregate
       uploads triggered by the U key.  Failed payloads are queued in the
       retry file via ``save_failed_upload()``.

    2. **Live event** – ``upload_live_event()`` sends one measurement per
       button press so the website reflects mood changes quickly.  Uses the
       same endpoint and retry file so no events are lost if offline.

    3. **Retry buffer** – ``retry_pending_uploads()`` re-sends anything stored
       in ``pending_uploads.json`` (from failed hourly or live-event uploads).
       Both tracks share the same file; the server endpoint accepts all formats.

    Duplicate-avoidance strategy
    ----------------------------
    * Hourly uploads are gated by ``last_uploaded_hour`` in main.py.
    * Manual aggregate uploads advance the same checkpoint, so the same window
      is never uploaded twice.
    * Live-event uploads are independent point-in-time measurements and do not
      affect the aggregate checkpoint.
    * A 409 response from the server is treated as success so stale retries do
      not loop endlessly.
    """

    def __init__(
        self,
        server_base_url: str,
        upload_endpoint: str,
        health_endpoint: str = "/api/v1/health",
        device_token: str = "",
        retry_file: str = "device/pending_uploads.json",
        timeout_seconds: int = 10,
    ) -> None:
        self.server_base_url = server_base_url.rstrip("/")
        self.upload_endpoint = upload_endpoint
        self.health_endpoint = health_endpoint
        self.timeout = timeout_seconds
        self.retry_file = Path(retry_file)
        self.retry_file.parent.mkdir(parents=True, exist_ok=True)
        self.request_headers = {"X-Device-Token": device_token.strip()} if device_token.strip() else {}

    def check_server_health(self) -> bool:
        """Returns True if the server responds to the health endpoint."""
        try:
            url = f"{self.server_base_url}{self.health_endpoint}"
            resp = requests.get(url, headers=self.request_headers, timeout=self.timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def upload_hourly_payload(self, payload: HourlyUploadPayload) -> tuple[bool, str]:
        """Upload one hourly payload. Returns (success, status_message)."""
        url = f"{self.server_base_url}{self.upload_endpoint}"
        body = self._payload_to_dict(payload)
        try:
            resp = requests.post(url, json=body, headers=self.request_headers, timeout=self.timeout)
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
                    headers=self.request_headers,
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

    def upload_live_event(
        self,
        mood: str,
        reading: SensorReading,
        timestamp: datetime,
    ) -> tuple[bool, str]:
        """Upload a single button-press event immediately (live-event track).

        The payload uses the same format as the hourly aggregate so that the
        server endpoint (device_ingest.php) can store it in ``measurements``
        without any schema changes.  A mood_counts dict with a single count for
        the pressed mood is used; the server derives the mood label from it.

        On failure the payload is queued in the shared retry file via
        ``save_failed_dict()``, so no live event is lost while offline.
        """
        mood_counts = {"good": 0, "neutral": 0, "bad": 0}
        if mood in mood_counts:
            mood_counts[mood] = 1
        body = {
            "mood_counts": mood_counts,
            "sensor_avg": {
                "temperature_c": round(reading.temperature_c, 2),
                "humidity_pct": round(reading.humidity_pct, 2),
                "co2_ppm": int(round(reading.co2_ppm)),
            },
            "created_at": timestamp.isoformat(),
        }
        url = f"{self.server_base_url}{self.upload_endpoint}"
        try:
            resp = requests.post(url, json=body, headers=self.request_headers, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return True, "live-ok"
            if resp.status_code == 409:
                return True, "live-duplicate"
            return False, f"live-http-{resp.status_code}"
        except requests.ConnectionError:
            return False, "live-connection-error"
        except requests.Timeout:
            return False, "live-timeout"
        except requests.RequestException as exc:
            return False, str(exc)

    def save_failed_dict(self, body: dict) -> None:
        """Append an arbitrary payload dict to the retry file.

        Used to persist failed live-event uploads so they are retried by
        ``retry_pending_uploads()`` when connectivity is restored.
        """
        pending = self._read_pending()
        pending.append(body)
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
