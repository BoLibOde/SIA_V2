import importlib
import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace

from device.models import MoodCounts, SensorReading


def _install_fake_device_modules() -> None:
    fake_gpio = types.SimpleNamespace(
        HIGH=1,
        LOW=0,
        BCM=11,
        IN=0,
        PUD_UP=1,
        setmode=lambda *args, **kwargs: None,
        setup=lambda *args, **kwargs: None,
        input=lambda *args, **kwargs: 1,
        cleanup=lambda *args, **kwargs: None,
    )
    fake_rpi = types.ModuleType("RPi")
    fake_rpi.GPIO = fake_gpio
    sys.modules.setdefault("RPi", fake_rpi)
    sys.modules.setdefault("RPi.GPIO", fake_gpio)

    class _FakeRect:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    fake_pygame = types.ModuleType("pygame")
    fake_pygame.FULLSCREEN = 0
    fake_pygame.QUIT = 0
    fake_pygame.KEYDOWN = 1
    fake_pygame.K_ESCAPE = 27
    fake_pygame.K_u = ord("u")
    fake_pygame.K_r = ord("r")
    fake_pygame.Surface = object
    fake_pygame.Rect = _FakeRect
    fake_pygame.init = lambda: None
    fake_pygame.quit = lambda: None
    fake_pygame.font = types.SimpleNamespace(init=lambda: None, SysFont=lambda *args, **kwargs: None)
    fake_pygame.display = types.SimpleNamespace(
        set_mode=lambda *args, **kwargs: None,
        set_caption=lambda *args, **kwargs: None,
        flip=lambda: None,
    )
    fake_pygame.image = types.SimpleNamespace(load=lambda *args, **kwargs: types.SimpleNamespace(convert_alpha=lambda: None))
    fake_pygame.transform = types.SimpleNamespace(smoothscale=lambda image, size: None)
    fake_pygame.draw = types.SimpleNamespace(rect=lambda *args, **kwargs: None)
    fake_pygame.event = types.SimpleNamespace(get=lambda: [])
    sys.modules.setdefault("pygame", fake_pygame)


_install_fake_device_modules()
device_main = importlib.import_module("device.main")


class _FakeSensorService:
    def __init__(self, latest_reading: SensorReading | None) -> None:
        self.latest_reading = latest_reading

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_latest_reading(self) -> SensorReading | None:
        return self.latest_reading

    def get_hour_samples(self) -> list[SensorReading]:
        return []

    def discard_samples_before(self, cutoff) -> None:
        pass

    def get_status_text(self) -> str:
        return "OK" if self.latest_reading is not None else "FEHLER"

    def has_data(self) -> bool:
        return self.latest_reading is not None

    def is_hardware_active(self) -> bool:
        return self.latest_reading is not None


class _FakeGpioHandler:
    def __init__(self, queue: list[str]) -> None:
        self.queue = list(queue)
        self.hourly_counts = MoodCounts()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def update(self) -> None:
        pass

    def get_hourly_counts(self) -> MoodCounts:
        return self.hourly_counts

    def get_daily_display_counts(self) -> MoodCounts:
        return MoodCounts()

    def reset_daily_display_counts(self) -> None:
        pass

    def pop_live_events(self) -> list[str]:
        events, self.queue = self.queue, []
        return events

    def requeue_live_events(self, moods: list[str]) -> None:
        self.queue = list(moods) + self.queue

    def clear_hourly_counts(self) -> None:
        self.hourly_counts = MoodCounts()


class _FakeUploadService:
    def __init__(
        self,
        live_result: tuple[bool, str],
        retry_result: tuple[int, int],
        hourly_result: tuple[bool, str] = (True, "ok"),
        today_counts_results: list[tuple[bool, MoodCounts | None, str, str]] | None = None,
    ) -> None:
        self.live_result = live_result
        self.retry_result = retry_result
        self.hourly_result = hourly_result
        self.today_counts_results = list(today_counts_results or [(False, None, "", "today-offline")])
        self.live_calls: list[tuple[str, SensorReading, datetime]] = []
        self.hourly_calls: list[object] = []
        self.today_count_calls: list[str] = []

    def check_server_health(self) -> bool:
        return True

    def upload_live_event(self, mood: str, reading: SensorReading, timestamp: datetime) -> tuple[bool, str]:
        self.live_calls.append((mood, reading, timestamp))
        return self.live_result

    def fetch_today_counts(self, device_id: str, location_id: int | None = None) -> tuple[bool, MoodCounts | None, str, str]:
        self.today_count_calls.append(device_id)
        if len(self.today_counts_results) > 1:
            return self.today_counts_results.pop(0)
        return self.today_counts_results[0]

    def retry_pending_uploads(self) -> tuple[int, int]:
        return self.retry_result

    def upload_hourly_payload(self, payload) -> tuple[bool, str]:
        self.hourly_calls.append(payload)
        return self.hourly_result

    def save_failed_upload(self, payload) -> None:
        pass


class _FakeUI:
    def __init__(self) -> None:
        self.action_upload = False
        self.action_reset_daily = False
        self._handle_calls = 0
        self.drawn_statuses: list[str] = []
        self.drawn_counts: list[MoodCounts | None] = []
        self.drawn_pending_counts: list[MoodCounts] = []

    def handle_events(self) -> bool:
        self._handle_calls += 1
        return self._handle_calls == 1

    def draw(
        self,
        latest,
        daily_counts,
        pending_counts,
        server_connected,
        last_upload_status,
        operating_mode="online",
        sensor_status_text="FEHLER",
        sensor_has_data=False,
        sensor_hardware_active=False,
    ) -> None:
        self.drawn_counts.append(daily_counts)
        self.drawn_pending_counts.append(pending_counts)
        self.drawn_statuses.append(last_upload_status)

    def close(self) -> None:
        pass


class _FakeAggregationService:
    def __init__(self, payload: object | None = "payload") -> None:
        self.payload = payload
        self.hourly_calls: list[datetime] = []
        self.min15_calls: list[datetime] = []
        self.window_called = False

    def build_hourly_payload(self, *, device_id, mood_counts, sensor_samples, now):
        self.hourly_calls.append(now)
        return self.payload

    def build_15min_payload(self, *, device_id, sensor_samples, now):
        self.min15_calls.append(now)
        return self.payload

    def build_window_payload(self, *args, **kwargs):
        self.window_called = True
        raise AssertionError("build_window_payload should not be used for manual uploads")


def _build_app(
    monkeypatch,
    *,
    latest_reading: SensorReading | None,
    queue: list[str],
    live_result=(True, "live-ok"),
    retry_result=(0, 0),
    hourly_result=(True, "ok"),
    aggregation_payload: object | None = "payload",
    today_counts_results: list[tuple[bool, MoodCounts | None, str, str]] | None = None,
):
    config = SimpleNamespace(
        sensor_interval_seconds=5,
        simulation_mode=True,
        enable_simulation_fallback=False,
        good_button_pin=1,
        neutral_button_pin=2,
        bad_button_pin=3,
        server_base_url="http://example.local",
        upload_endpoint="/device_ingest.php",
        health_endpoint="/device_ingest.php",
        today_counts_endpoint="/device_today_counts.php",
        device_token="secret-token",
        retry_file_path="device/pending_uploads.json",
        upload_timeout_seconds=10,
        display_width=800,
        display_height=600,
        fullscreen=False,
        device_id="pi-room-01",
        ui_refresh_seconds=0,
        operating_mode="online",
        offline_data_file="device/tagesgesamt.json",
    )
    sensor_service = _FakeSensorService(latest_reading)
    gpio_handler = _FakeGpioHandler(queue)
    upload_service = _FakeUploadService(live_result, retry_result, hourly_result, today_counts_results)
    aggregation_service = _FakeAggregationService(aggregation_payload)
    ui = _FakeUI()

    # Fake OfflineStorage that does nothing (no disk I/O in tests)
    class _FakeOfflineStorage:
        def load_daily_counts(self):
            return MoodCounts()

        def save_daily_counts(self, counts) -> None:
            pass

        def reset_on_new_day(self, current):
            return False, current

    _fixed_monotonic = 1000.0  # large fixed value so health-check interval never fires

    monkeypatch.setattr(device_main, "DeviceConfig", lambda: config)
    monkeypatch.setattr(device_main, "SensorService", lambda **kwargs: sensor_service)
    monkeypatch.setattr(device_main, "GpioHandler", lambda **kwargs: gpio_handler)
    monkeypatch.setattr(device_main, "AggregationService", lambda: aggregation_service)
    monkeypatch.setattr(device_main, "UploadService", lambda **kwargs: upload_service)
    monkeypatch.setattr(device_main, "OfflineStorage", lambda **kwargs: _FakeOfflineStorage())
    monkeypatch.setattr(device_main, "DeviceUI", lambda **kwargs: ui)
    monkeypatch.setattr(
        device_main,
        "time",
        types.SimpleNamespace(
            sleep=lambda seconds: None,
            monotonic=lambda: _fixed_monotonic,
        ),
    )
    monkeypatch.setattr(device_main.DeviceApp, "_try_periodic_sensor_upload", lambda self, now: None)

    return device_main.DeviceApp(), gpio_handler, upload_service, ui


def test_run_requeues_live_events_without_sensor_reading(monkeypatch) -> None:
    app, gpio_handler, upload_service, _ = _build_app(
        monkeypatch,
        latest_reading=None,
        queue=["bad"],
    )

    app.run()

    assert upload_service.live_calls == []
    assert gpio_handler.queue == ["bad"]
    assert "Live wartet: 1 ohne Sensordaten" in app._last_upload_status


def test_run_uploads_each_live_event_with_aware_timestamps(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, upload_service, _ = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=["bad", "neutral"],
    )

    app.run()

    assert [call[0] for call in upload_service.live_calls] == ["bad", "neutral"]
    assert all(call[2].tzinfo is not None for call in upload_service.live_calls)
    assert "Live: neutral live-ok" in app._last_upload_status


def test_run_shows_optimistic_pending_counts_when_refresh_fails(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, _, ui = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=["good"],
        live_result=(False, "live-timeout"),
        today_counts_results=[(True, MoodCounts(good=5, neutral=1, bad=0), "2024-01-01", "today-ok")],
    )

    app.run()

    assert ui.drawn_counts[-1] == MoodCounts(good=6, neutral=1, bad=0)
    assert ui.drawn_pending_counts[-1] == MoodCounts(good=1, neutral=0, bad=0)


def test_run_keeps_counts_uninitialized_until_first_successful_refresh(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, _, ui = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=["good"],
        live_result=(False, "live-timeout"),
        today_counts_results=[(False, None, "", "today-offline")],
    )

    app.run()

    assert ui.drawn_counts[-1] is None
    assert ui.drawn_pending_counts[-1] == MoodCounts(good=1, neutral=0, bad=0)


def test_run_reconciles_pending_counts_after_successful_refresh(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, upload_service, ui = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=["good"],
        today_counts_results=[
            (True, MoodCounts(good=5, neutral=1, bad=0), "2024-01-01", "today-ok"),
            (True, MoodCounts(good=6, neutral=1, bad=0), "2024-01-01", "today-ok"),
        ],
    )

    app.run()

    assert upload_service.today_count_calls == ["pi-room-01", "pi-room-01"]
    assert ui.drawn_counts[-1] == MoodCounts(good=6, neutral=1, bad=0)
    assert ui.drawn_pending_counts[-1] == MoodCounts()


def test_run_reconciles_only_uploaded_pending_counts_without_startup_base(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, _, ui = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=["good", "good"],
        live_result=(True, "live-ok"),
        today_counts_results=[
            (False, None, "", "today-offline"),
            (True, MoodCounts(good=6, neutral=0, bad=0), "2024-01-01", "today-ok"),
        ],
    )

    app.run()

    assert ui.drawn_counts[-1] == MoodCounts(good=6, neutral=0, bad=0)
    assert ui.drawn_pending_counts[-1] == MoodCounts()


def test_run_surfaces_retry_buffer_activity(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, _, ui = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=[],
        retry_result=(1, 2),
    )

    app.run()

    assert ui.drawn_statuses[-1].endswith("Retry: 1 gesendet, 2 offen")


def test_manual_upload_uses_latest_completed_15min_window(monkeypatch) -> None:
    reading = SensorReading(
        temperature_c=21.5,
        humidity_pct=41.0,
        co2_ppm=615,
        timestamp=datetime(2024, 1, 1, 9, 30, 0, tzinfo=UTC),
    )
    app, _, upload_service, _ = _build_app(
        monkeypatch,
        latest_reading=reading,
        queue=[],
    )

    fixed_now = datetime(2024, 1, 1, 12, 34, 56, tzinfo=UTC)
    fake_datetime = types.SimpleNamespace(now=lambda tz=None: fixed_now)
    monkeypatch.setattr(device_main, "datetime", fake_datetime)

    app._manual_upload()

    assert app.aggregation_service.min15_calls == [fixed_now]
    assert app.aggregation_service.window_called is False
    assert upload_service.hourly_calls == ["payload"]
    # For 12:34:56 the latest completed 15-min boundary is 12:30
    assert app.last_uploaded_period_end == datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC)
