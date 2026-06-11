import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class DeviceConfig:
    device_id: str = field(default_factory=lambda: os.getenv("SIA_DEVICE_ID", "pi-room-01"))
    good_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_GOOD_PIN", "17")))
    neutral_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_NEUTRAL_PIN", "27")))
    bad_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_BAD_PIN", "22")))

    sensor_interval_seconds: int = field(default_factory=lambda: int(os.getenv("SIA_SENSOR_INTERVAL", "5")))
    ui_refresh_seconds: int = field(default_factory=lambda: int(os.getenv("SIA_UI_REFRESH", "1")))

    display_width: int = field(default_factory=lambda: int(os.getenv("SIA_DISPLAY_WIDTH", "1024")))
    display_height: int = field(default_factory=lambda: int(os.getenv("SIA_DISPLAY_HEIGHT", "600")))
    fullscreen: bool = field(default_factory=lambda: _env_bool("SIA_FULLSCREEN", True))

    # Tailscale / server connection – set SIA_SERVER_URL to override the Tailscale IP or hostname
    server_base_url: str = field(default_factory=lambda: os.getenv("SIA_SERVER_URL", "http://100.74.7.35:8000"))
    upload_endpoint: str = field(default_factory=lambda: os.getenv("SIA_UPLOAD_ENDPOINT", "/api/v1/ingest/hourly"))
    health_endpoint: str = field(default_factory=lambda: os.getenv("SIA_HEALTH_ENDPOINT", "/api/v1/health"))

    upload_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("SIA_UPLOAD_TIMEOUT", "10")))

    # When True, the sensor service uses simulated values (no real hardware needed)
    simulation_mode: bool = field(default_factory=lambda: _env_bool("SIA_SIMULATION", False))

    # Path for storing failed uploads that will be retried
    retry_file_path: str = field(default_factory=lambda: os.getenv("SIA_RETRY_FILE", "device/pending_uploads.json"))

