import json
from datetime import datetime
from pathlib import Path

import requests

from device.models import HourlyUploadPayload, SensorReading


class UploadService:
    """Handles all three upload tracks for the Raspberry Pi device.

    Upload tracks
    -------------
    1. **Hourly aggregate** – ``upload_hourly_payload()`` sends one
       60-minute sensor-average window. Called by ``_try_hourly_upload()`` in
       main.py and also used for manual aggregate uploads triggered by the U
       key. Failed payloads are queued in the retry file via
       ``save_failed_upload()``.

    2. **Live event** – ``upload_live_event()`` sends one measurement per
       button press so the website reflects mood changes quickly.  Uses the
       same endpoint and retry file so no events are lost if offline.

    3. **Retry buffer** – ``retry_pending_uploads()`` re-sends anything stored
       in ``pending_uploads.json`` (from failed hourly or live-event uploads).
       Both tracks share the same file; the server endpoint accepts both
       payload types and stores them separately.

    Duplicate-avoidance strategy
    ----------------------------
    * Hourly uploads are gated by ``last_uploaded_hour`` in main.py.
    * Manual aggregate uploads advance the same checkpoint, so the same window
      is never uploaded twice.
    * Live-event uploads are independent point-in-time measurements and do not
      affect the aggregate checkpoint.
    * A 409 response from the server is treated as success so stale retries do
      not loop endlessly.
    * ``save_failed_upload`` skips appending if an identical hourly aggregate
      (same device_id, period_start, period_end) is already queued, preventing
      repeated failed attempts within the same upload window from growing the
      retry file.
    * ``retry_pending_uploads`` deduplicates the pending list on load so that
      any previously accumulated duplicate entries are collapsed before retrying.
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

    def retry_pending_uploads(self) -> tuple[int, int]:
        """Retry buffered uploads and return (sent_count, remaining_count).

        Duplicate hourly aggregate entries (same device_id + period_start +
        period_end) accumulated from previous failures are collapsed before
        retrying so that only one copy of each unique aggregate is sent.
        """
        pending = self._read_pending()
        if not pending:
            return 0, 0

        pending = self._dedup_pending(pending)

        still_pending = []
        sent_count = 0
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
                else:
                    sent_count += 1
            except requests.RequestException:
                still_pending.append(body)

        self._write_pending(still_pending)
        return sent_count, len(still_pending)

    def save_failed_upload(self, payload: HourlyUploadPayload) -> None:
        """Append a failed hourly aggregate to the retry file.

        Skips the append if an entry for the same device_id/period_start/
        period_end is already queued, preventing the retry file from growing
        with many identical copies when the server is temporarily unreachable.
        """
        new_entry = self._payload_to_dict(payload)
        pending = self._read_pending()
        for entry in pending:
            if (
                entry.get("device_id") == new_entry["device_id"]
                and entry.get("period_start") == new_entry["period_start"]
                and entry.get("period_end") == new_entry["period_end"]
            ):
                return
        pending.append(new_entry)
        self._write_pending(pending)

    def upload_live_event(
        self,
        mood: str,
        reading: SensorReading,
        timestamp: datetime,
    ) -> tuple[bool, str]:
        """Upload a single button-press event immediately (live-event track).

        The payload uses the direct PHP measurement format so that one button
        press becomes exactly one mood row in ``measurements``.

        On failure the payload is automatically queued in the shared retry file
        so no live event is lost while offline.
        """
        mood_map = {
            "good": "positiv",
            "neutral": "neutral",
            "bad": "negativ",
        }
        normalized_mood = mood_map.get(mood, mood)
        body = {
            "upload_type": "mood_live",
            "mood": normalized_mood,
            "temperature": round(reading.temperature_c, 2),
            "humidity": round(reading.humidity_pct, 2),
            "co2": int(round(reading.co2_ppm)),
            "created_at": timestamp.isoformat(),
        }
        url = f"{self.server_base_url}{self.upload_endpoint}"
        try:
            resp = requests.post(url, json=body, headers=self.request_headers, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return True, "live-ok"
            if resp.status_code == 409:
                return True, "live-duplicate"
            self.save_failed_dict(body)
            return False, f"live-http-{resp.status_code}"
        except requests.ConnectionError:
            self.save_failed_dict(body)
            return False, "live-connection-error"
        except requests.Timeout:
            self.save_failed_dict(body)
            return False, "live-timeout"
        except requests.RequestException as exc:
            self.save_failed_dict(body)
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
            "upload_type": "sensor_hourly",
            "device_id": payload.device_id,
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
            "sensor_avg": {
                "temperature_c": payload.sensor_avg_temperature_c,
                "humidity_pct": payload.sensor_avg_humidity_pct,
                "co2_ppm": payload.sensor_avg_co2_ppm,
            },
            "sample_count": payload.sample_count,
        }

    def _dedup_pending(self, payloads: list[dict]) -> list[dict]:
        """Collapse duplicate hourly aggregate entries in the pending list.

        Two entries are considered duplicates when they share the same
        device_id, period_start, and period_end.  Live-event entries (which
        have a ``created_at`` field instead of ``period_start``) are kept as-is
        because each represents a unique button-press event.
        """
        seen: set[tuple[str, str, str]] = set()
        deduped: list[dict] = []
        for entry in payloads:
            period_start = entry.get("period_start")
            if period_start is not None:
                key = (
                    entry.get("device_id", ""),
                    period_start,
                    entry.get("period_end", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
            deduped.append(entry)
        return deduped

    def _read_pending(self) -> list[dict]:
        if not self.retry_file.exists():
            return []
        try:
            return json.loads(self.retry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write_pending(self, payloads: list[dict]) -> None:
        self.retry_file.write_text(json.dumps(payloads, indent=2), encoding="utf-8")
