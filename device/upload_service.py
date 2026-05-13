import requests

from device.models import HourlyUploadPayload


class UploadService:
    def __init__(self, server_base_url: str, upload_endpoint: str) -> None:
        self.server_base_url = server_base_url.rstrip("/")
        self.upload_endpoint = upload_endpoint

    def upload_hourly_payload(self, payload: HourlyUploadPayload) -> bool:
        url = f"{self.server_base_url}{self.upload_endpoint}"
        request_body = {
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

        try:
            response = requests.post(url, json=request_body, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
