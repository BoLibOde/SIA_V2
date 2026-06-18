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
    good_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_GOOD_PIN", "27")))
    neutral_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_NEUTRAL_PIN", "22")))
    bad_button_pin: int = field(default_factory=lambda: int(os.getenv("SIA_BAD_PIN", "17")))

    sensor_interval_seconds: int = field(default_factory=lambda: int(os.getenv("SIA_SENSOR_INTERVAL", "5")))
    ui_refresh_seconds: float = field(default_factory=lambda: float(os.getenv("SIA_UI_REFRESH", "0.05")))

    display_width: int = field(default_factory=lambda: int(os.getenv("SIA_DISPLAY_WIDTH", "1024")))
    display_height: int = field(default_factory=lambda: int(os.getenv("SIA_DISPLAY_HEIGHT", "600")))
    fullscreen: bool = field(default_factory=lambda: _env_bool("SIA_FULLSCREEN", True))

    # Production defaults target the PHP website ingest endpoint.
    # For FastAPI development, override via SIA_SERVER_URL/SIA_UPLOAD_ENDPOINT/SIA_HEALTH_ENDPOINT.
    server_base_url: str = field(default_factory=lambda: os.getenv("SIA_SERVER_URL", "http://100.74.7.35"))
    upload_endpoint: str = field(default_factory=lambda: os.getenv("SIA_UPLOAD_ENDPOINT", "/device_ingest.php"))
    health_endpoint: str = field(default_factory=lambda: os.getenv("SIA_HEALTH_ENDPOINT", "/device_ingest.php"))
    today_counts_endpoint: str = field(default_factory=lambda: os.getenv("SIA_TODAY_COUNTS_ENDPOINT", "/device_today_counts.php"))
    device_token: str = field(default_factory=lambda: os.getenv("SIA_DEVICE_TOKEN", ""))

    upload_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("SIA_UPLOAD_TIMEOUT", "10")))

    # When True, the sensor service uses simulated values (no real hardware needed)
    simulation_mode: bool = field(default_factory=lambda: _env_bool("SIA_SIMULATION", False))

    # Path for storing failed uploads that will be retried
    retry_file_path: str = field(default_factory=lambda: os.getenv("SIA_RETRY_FILE", "device/pending_uploads.json"))
