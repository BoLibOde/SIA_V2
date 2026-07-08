import time
from datetime import UTC, datetime

from device.aggregation_service import AggregationService
from device.config import DeviceConfig
from device.gpio_handler import GpioHandler
from device.models import MoodCounts
from device.offline_storage import OfflineStorage
from device.sensor_service import SensorService
from device.ui import DeviceUI
from device.upload_service import UploadService

# Exponential-backoff bounds for the server health-check interval (seconds).
_HEALTH_CHECK_MIN_S: float = 30.0
_HEALTH_CHECK_MAX_S: float = 60.0


class DeviceApp:
    def __init__(
        self,
        operating_mode: str = "online",
        enable_simulation_fallback: bool | None = None,
    ) -> None:
        self.config = DeviceConfig()
        # operating_mode from the startup menu takes priority; fall back to config value.
        self.operating_mode: str = operating_mode if operating_mode in ("online", "offline") else self.config.operating_mode
        self.enable_simulation_fallback = (
            self.config.enable_simulation_fallback
            if enable_simulation_fallback is None
            else enable_simulation_fallback
        )
        self.sensor_service = SensorService(
            read_interval_seconds=self.config.sensor_interval_seconds,
            simulation_mode=self.config.simulation_mode,
            enable_simulation_fallback=self.enable_simulation_fallback,
        )
        self.gpio_handler = GpioHandler(
            good_pin=self.config.good_button_pin,
            neutral_pin=self.config.neutral_button_pin,
            bad_pin=self.config.bad_button_pin,
        )
        self.aggregation_service = AggregationService()
        self.upload_service = UploadService(
            server_base_url=self.config.server_base_url,
            upload_endpoint=self.config.upload_endpoint,
            health_endpoint=self.config.health_endpoint,
            today_counts_endpoint=self.config.today_counts_endpoint,
            device_token=self.config.device_token,
            retry_file=self.config.retry_file_path,
            timeout_seconds=self.config.upload_timeout_seconds,
        )
        self.offline_storage = OfflineStorage(data_file=self.config.offline_data_file)
        self.ui = DeviceUI(
            width=self.config.display_width,
            height=self.config.display_height,
            fullscreen=self.config.fullscreen,
            device_id=self.config.device_id,
        )

        self.running = False
        self.last_uploaded_period_end: datetime | None = None
        self.today_base_counts: MoodCounts | None = None
        self.today_pending_counts = MoodCounts()
        self.today_uploaded_pending_counts = MoodCounts()
        self.today_counts_date = ""

        # Status shown in the UI status bar
        self._server_connected: bool = False
        self._last_upload_status: str = "—"

        # Time-based server health check with exponential backoff.
        # Initialise _last_health_check to now so the first automatic check
        # happens after _HEALTH_CHECK_MIN_S, not immediately.
        self._health_check_interval: float = _HEALTH_CHECK_MIN_S
        self._last_health_check: float = time.monotonic()

        if self.operating_mode == "offline":
            # Pure offline: load counts from local storage only
            self.today_base_counts = self.offline_storage.load_daily_counts()
            self.today_counts_date = datetime.now().date().isoformat()
        else:
            # Online: check server health and fetch today's counts
            self._server_connected = self.upload_service.check_server_health()
            today_counts_ok = self._refresh_today_counts()
            self._server_connected = self._server_connected or today_counts_ok

    def run(self) -> None:
        self.running = True
        self.sensor_service.start()
        self.gpio_handler.start()

        try:
            while self.running:
                now = datetime.now(UTC)
                latest = self.sensor_service.get_latest_reading()
                self.gpio_handler.update()

                if not self.ui.handle_events():
                    self.running = False
                    break

                if self.operating_mode == "offline":
                    self._run_offline_tick(now)
                else:
                    self._run_online_tick(now, latest)

                self.ui.draw(
                    latest,
                    self._get_display_counts(),
                    self.today_pending_counts,
                    self._server_connected,
                    self._last_upload_status,
                    self.operating_mode,
                    self.sensor_service.get_status_text(),
                    self.sensor_service.has_data(),
                    self.sensor_service.is_hardware_active(),
                )

                time.sleep(self.config.ui_refresh_seconds)
        except KeyboardInterrupt:
            print("Stopping device app...")
        finally:
            self.shutdown()

    def _run_offline_tick(self, now: datetime) -> None:
        """Main-loop body for pure offline mode.

        Button presses are recorded directly to local storage; no server
        communication is attempted.  The daily counter resets automatically
        at midnight.
        """
        # Midnight rollover
        was_reset, new_counts = self.offline_storage.reset_on_new_day(
            self.today_base_counts or MoodCounts()
        )
        if was_reset:
            self.today_base_counts = new_counts
            self.today_pending_counts = MoodCounts()
            self.today_uploaded_pending_counts = MoodCounts()
            self.today_counts_date = now.astimezone().date().isoformat()

        # Handle keyboard actions (upload / reset keys are no-ops in offline mode)
        if self.ui.action_reset_daily:
            self.today_base_counts = MoodCounts()
            self.today_pending_counts = MoodCounts()
            self.today_uploaded_pending_counts = MoodCounts()
            self.offline_storage.save_daily_counts(MoodCounts())
            self._set_upload_status(now, "Tageszähler zurückgesetzt (lokal)")

        # Button presses → increment + persist immediately
        live_events = self.gpio_handler.pop_live_events()
        if live_events:
            for mood in live_events:
                self._increment_mood_count(self.today_pending_counts, mood)
            combined = self._get_display_counts() or MoodCounts()
            self.offline_storage.save_daily_counts(combined)

    def _run_online_tick(self, now: datetime, latest) -> None:
        """Main-loop body for online mode (with or without server connection).

        Preserves all original upload behaviour.  Health checks are now
        time-based with exponential back-off to avoid hammering the server
        when it is temporarily unreachable.
        """
        # Handle keyboard (or future GPIO button) actions
        if self.ui.action_upload:
            self._manual_upload()
        if self.ui.action_reset_daily:
            if self._refresh_today_counts():
                self._set_upload_status(now, "Tageszähler aktualisiert")
            else:
                self._set_upload_status(now, "Tageszähler-Abruf fehlgeschlagen")

        status_updated = self.ui.action_upload or self.ui.action_reset_daily

        # Live-event track: upload one measurement per button press so
        # the website reflects mood changes without waiting for the next
        # hourly sensor aggregate window.
        live_events = self.gpio_handler.pop_live_events()
        if live_events:
            self._apply_pending_live_events(live_events)
            if latest is None:
                self.gpio_handler.requeue_live_events(live_events)
                self._set_upload_status(now, f"Live wartet: {len(live_events)} ohne Sensordaten")
                status_updated = True
            else:
                any_live_success = False
                for mood in live_events:
                    success, status_msg = self.upload_service.upload_live_event(mood, latest, now)
                    self._server_connected = success
                    if success:
                        any_live_success = True
                        self._mark_uploaded_live_event(mood)
                        self._set_upload_status(now, f"Live: {mood} {status_msg}")
                    else:
                        self._set_upload_status(
                            now,
                            f"Live fehlgeschlagen (gepuffert): {mood} {status_msg}",
                        )
                    status_updated = True
                if any_live_success:
                    self._refresh_today_counts()

                # Also mirror accepted button presses to offline storage so the
                # counts are available when the server is temporarily offline.
                combined = self._get_display_counts() or MoodCounts()
                self.offline_storage.save_daily_counts(combined)

        retried_count, remaining_count = self.upload_service.retry_pending_uploads()
        if retried_count:
            self._refresh_today_counts()
        if (retried_count or remaining_count) and not status_updated:
            self._set_upload_status(now, f"Retry: {retried_count} gesendet, {remaining_count} offen")
        self._try_periodic_sensor_upload(now)

        # Time-based server health check with exponential backoff.
        # Interval starts at 30 s, doubles on each failure (max 60 s),
        # and resets to 30 s after a successful connection.
        now_ts = time.monotonic()
        if now_ts - self._last_health_check >= self._health_check_interval:
            was_connected = self._server_connected
            self._server_connected = self.upload_service.check_server_health()
            self._last_health_check = now_ts
            if self._server_connected:
                self._health_check_interval = _HEALTH_CHECK_MIN_S
                if not was_connected:
                    # Reconnected – refresh counts from server
                    self._refresh_today_counts()
            else:
                # Back off until max interval
                self._health_check_interval = min(
                    self._health_check_interval * 2, _HEALTH_CHECK_MAX_S
                )

    def shutdown(self) -> None:
        self.running = False
        self.sensor_service.stop()
        self.gpio_handler.stop()
        self.ui.close()

    def _manual_upload(self) -> None:
        """Manual aggregate upload triggered by the U key.

        Upload tracks performed in order:
        1. Retry pending uploads (live-event + aggregate failures from the buffer).
        2. Build an aggregate payload for the latest completed 15-minute sensor
           window and upload it. The aggregate checkpoint is advanced so the
           same window is never uploaded twice.
        3. If there is nothing new to aggregate (no sensor samples in the
           completed window), show a 'nothing new' status instead of sending an
           empty payload.

        Live-event uploads are NOT affected by this call; they run independently
        in the main loop and are not double-counted here.
        """
        now = datetime.now(UTC)

        # Step 1: flush existing retry buffer
        retried_count, remaining_count = self.upload_service.retry_pending_uploads()
        if retried_count or remaining_count:
            self._set_upload_status(now, f"Retry vor Manuell: {retried_count} gesendet, {remaining_count} offen")

        # Step 2: upload the latest completed 15-minute sensor window only
        quarter = (now.minute // 15) * 15
        period_end = now.replace(minute=quarter, second=0, microsecond=0)
        if self.last_uploaded_period_end == period_end:
            self._set_upload_status(now, "Manuell: nichts Neues")
            self._server_connected = self.upload_service.check_server_health()
            return

        payload = self.aggregation_service.build_15min_payload(
            device_id=self.config.device_id,
            sensor_samples=self.sensor_service.get_hour_samples(),
            now=now,
        )

        if payload is None:
            self._set_upload_status(now, "Manuell: nichts Neues")
            self._server_connected = self.upload_service.check_server_health()
            return

        success, status_msg = self.upload_service.upload_hourly_payload(payload)
        self._server_connected = success

        if success:
            self.last_uploaded_period_end = period_end
            self._set_upload_status(now, f"Manuell: {status_msg}")
            self.sensor_service.discard_samples_before(period_end)
        else:
            self.upload_service.save_failed_upload(payload)
            self._set_upload_status(now, f"Manuell fehlgeschlagen: {status_msg}")

    def _try_periodic_sensor_upload(self, now: datetime) -> None:
        """Trigger a 15-minute sensor aggregate upload.

        Fires within the first 5 seconds after every 15-minute boundary
        (HH:00, HH:15, HH:30, HH:45).  The same completed window is never
        uploaded twice: the checkpoint ``last_uploaded_period_end`` is
        advanced only after a successful upload.

        On failure the payload is queued for retry via
        ``save_failed_upload``; the checkpoint is NOT advanced so the same
        window can be retried in the next matching loop tick.

        After a successful upload all sensor samples older than
        ``period_end`` are discarded so they cannot re-appear in a later
        aggregate window.
        """
        if now.minute % 15 != 0 or now.second > 5:
            return

        period_end = now.replace(second=0, microsecond=0)
        if self.last_uploaded_period_end == period_end:
            return

        payload = self.aggregation_service.build_15min_payload(
            device_id=self.config.device_id,
            sensor_samples=self.sensor_service.get_hour_samples(),
            now=now,
        )

        if payload is None:
            return

        success, status_msg = self.upload_service.upload_hourly_payload(payload)
        self._server_connected = success

        if success:
            self._set_upload_status(now, f"Aggregat: {status_msg}")
            self.last_uploaded_period_end = period_end
            self.sensor_service.discard_samples_before(period_end)
        else:
            self.upload_service.save_failed_upload(payload)
            self._set_upload_status(now, f"Aggregat fehlgeschlagen: {status_msg}")

    def _set_upload_status(self, moment: datetime, message: str) -> None:
        if moment.tzinfo is None:
            timestamp = moment.strftime("%H:%M")
        else:
            timestamp = moment.astimezone().strftime("%H:%M")
        self._last_upload_status = f"{timestamp} {message}"
        print(self._last_upload_status, flush=True)

    def _refresh_today_counts(self) -> bool:
        success, counts, counts_date, _ = self.upload_service.fetch_today_counts(self.config.device_id)
        if not success or counts is None:
            # Server unavailable – use locally cached counts only when we have
            # no server baseline yet (first start with no connectivity).  If we
            # already have server data in memory we keep it as-is, because the
            # server counts are always more authoritative than the local cache.
            if self.today_base_counts is None:
                local = self.offline_storage.load_daily_counts()
                if local.total() > 0:
                    self.today_base_counts = local
                    self.today_counts_date = datetime.now().date().isoformat()
            return False

        previous_base = self.today_base_counts
        previous_date = self.today_counts_date

        if previous_date and counts_date and counts_date != previous_date:
            self.today_pending_counts = MoodCounts()
            self.today_uploaded_pending_counts = MoodCounts()
        else:
            self._reconcile_pending_counts(previous_base or MoodCounts(), counts)

        self.today_base_counts = counts
        self.today_counts_date = counts_date
        return True

    def _apply_pending_live_events(self, moods: list[str]) -> None:
        for mood in moods:
            self._increment_mood_count(self.today_pending_counts, mood)

    def _reconcile_pending_counts(self, previous_base: MoodCounts, new_base: MoodCounts) -> None:
        for mood in ("good", "neutral", "bad"):
            self._reconcile_pending_mood(
                mood,
                max(0, getattr(new_base, mood) - getattr(previous_base, mood)),
            )

    def _mark_uploaded_live_event(self, mood: str) -> None:
        self._increment_mood_count(self.today_uploaded_pending_counts, mood)

    def _reconcile_pending_mood(self, mood: str, server_delta: int) -> None:
        if server_delta <= 0:
            return

        uploaded_pending = getattr(self.today_uploaded_pending_counts, mood)
        reconciled = min(uploaded_pending, server_delta)
        if reconciled <= 0:
            return

        setattr(self.today_uploaded_pending_counts, mood, uploaded_pending - reconciled)
        setattr(
            self.today_pending_counts,
            mood,
            max(0, getattr(self.today_pending_counts, mood) - reconciled),
        )

    def _increment_mood_count(self, counts: MoodCounts, mood: str) -> None:
        if hasattr(counts, mood):
            setattr(counts, mood, getattr(counts, mood) + 1)

    def _get_display_counts(self) -> MoodCounts | None:
        if self.today_base_counts is None:
            return None

        return MoodCounts(
            good=self.today_base_counts.good + self.today_pending_counts.good,
            neutral=self.today_base_counts.neutral + self.today_pending_counts.neutral,
            bad=self.today_base_counts.bad + self.today_pending_counts.bad,
        )


if __name__ == "__main__":
    from device.startup_ui import StartupMenu

    _config = DeviceConfig()
    _menu = StartupMenu(
        width=_config.display_width,
        height=_config.display_height,
        fullscreen=_config.fullscreen,
        good_pin=_config.good_button_pin,
        neutral_pin=_config.neutral_button_pin,
        bad_pin=_config.bad_button_pin,
    )
    _selection = _menu.run()
    if isinstance(_selection, tuple):
        _mode, _enable_simulation_fallback = _selection
    else:
        _mode = _selection
        _enable_simulation_fallback = _config.enable_simulation_fallback
    app = DeviceApp(
        operating_mode=_mode,
        enable_simulation_fallback=_enable_simulation_fallback,
    )
    app.run()
