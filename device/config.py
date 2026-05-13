from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceConfig:
    device_id: str = "pi-room-01"
    good_button_pin: int = 17
    neutral_button_pin: int = 27
    bad_button_pin: int = 22
    sensor_interval_seconds: int = 5
    ui_refresh_seconds: int = 1
    display_width: int = 1024
    display_height: int = 600
    server_base_url: str = "http://localhost:8000"
    upload_endpoint: str = "/api/v1/ingest/hourly"
