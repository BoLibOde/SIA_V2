import time
from datetime import datetime, timedelta

from device.aggregation_service import AggregationService
from device.config import DeviceConfig
from device.gpio_handler import GpioHandler
from device.sensor_service import SensorService
from device.ui import DeviceUI
from device.upload_service import UploadService


class DeviceApp:
    def __init__(self) -> None:
        self.config = DeviceConfig()
        self.sensor_service = SensorService(
            read_interval_seconds=self.config.sensor_interval_seconds,
            simulation_mode=self.config.simulation_mode,
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
            device_token=self.config.device_token,
            retry_file=self.config.retry_file_path,
            timeout_seconds=self.config.upload_timeout_seconds,
        )
        self.ui = DeviceUI(
            width=self.config.display_width,
            height=self.config.display_height,
            fullscreen=self.config.fullscreen,
            device_id=self.config.device_id,
        )

        self.running = False
        self.last_uploaded_hour: datetime | None = None

        # Status shown in the UI status bar
        self._server_connected: bool = False
        self._last_upload_status: str = "—"

        # Check server health on startup
        self._server_connected = self.upload_service.check_server_health()

    def run(self) -> None:
        self.running = True
        self.sensor_service.start()
        self.gpio_handler.start()

        health_check_counter = 0

        try:
            while self.running:
                now = datetime.utcnow()
                latest = self.sensor_service.get_latest_reading()
                self.gpio_handler.update()
                hourly_counts = self.gpio_handler.get_hourly_counts()
                # Daily display counts are shown in the UI (reset at midnight or via R key).
                # They are independent of hourly_counts used for uploads.
                daily_counts = self.gpio_handler.get_daily_display_counts()

                if not self.ui.handle_events():
                    self.running = False
                    break

                # Handle keyboard (or future GPIO button) actions
                # To add physical buttons: check button flags from gpio_handler here
                # alongside self.ui.action_upload / self.ui.action_reset_daily.
                if self.ui.action_upload:
                    self._manual_upload()
                if self.ui.action_reset_daily:
                    self.gpio_handler.reset_daily_display_counts()
                    daily_counts = self.gpio_handler.get_daily_display_counts()
                    self._last_upload_status = f"{datetime.now().strftime('%H:%M')} Tageszähler zurückgesetzt"

                # Live-event track: upload one measurement per button press so
                # the website reflects mood changes without waiting for the next
                # hourly aggregate window.
                live_events = self.gpio_handler.pop_live_events()
                if live_events and latest is not None:
                    for mood in live_events:
                        ok, msg = self.upload_service.upload_live_event(mood, latest, now)
                        if not ok:
                            # Persist for retry so no live event is lost offline
                            mood_counts = {"good": 0, "neutral": 0, "bad": 0}
                            if mood in mood_counts:
                                mood_counts[mood] = 1
                            self.upload_service.save_failed_dict({
                                "mood_counts": mood_counts,
                                "sensor_avg": {
                                    "temperature_c": round(latest.temperature_c, 2),
                                    "humidity_pct": round(latest.humidity_pct, 2),
                                    "co2_ppm": int(round(latest.co2_ppm)),
                                },
                                "created_at": now.isoformat(),
                            })

                self.ui.draw(latest, daily_counts, self._server_connected, self._last_upload_status)
                self.upload_service.retry_pending_uploads()
                self._try_hourly_upload(now)

                # Refresh server connection status every ~30 loop ticks
                health_check_counter += 1
                if health_check_counter >= 30:
                    self._server_connected = self.upload_service.check_server_health()
                    health_check_counter = 0

                time.sleep(self.config.ui_refresh_seconds)
        except KeyboardInterrupt:
            print("Stopping device app...")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        self.sensor_service.stop()
        self.gpio_handler.stop()
        self.ui.close()

    def _manual_upload(self) -> None:
        """Manual aggregate upload triggered by the U key.

        Upload tracks performed in order:
        1. Retry pending uploads (hourly + live-event failures from the buffer).
        2. Build an aggregate payload for the window since the last successful
           aggregate upload and upload it.  The aggregate checkpoint is advanced
           so the same data is never uploaded twice.
        3. If there is nothing new to aggregate (no sensor samples in the window),
           show a 'nothing new' status instead of sending an empty payload.

        Live-event uploads are NOT affected by this call; they run independently
        in the main loop and are not double-counted here.
        """
        now = datetime.utcnow()

        # Step 1: flush existing retry buffer
        self.upload_service.retry_pending_uploads()

        # Step 2: aggregate the window since the last aggregate upload checkpoint
        period_start = self.last_uploaded_hour if self.last_uploaded_hour is not None else now - timedelta(hours=1)
        payload = self.aggregation_service.build_window_payload(
            device_id=self.config.device_id,
            mood_counts=self.gpio_handler.get_hourly_counts(),
            sensor_samples=self.sensor_service.get_hour_samples(),
            period_start=period_start,
            period_end=now,
        )

        if payload is None:
            self._last_upload_status = f"{now.strftime('%H:%M')} Manuell: nichts Neues"
            self._server_connected = self.upload_service.check_server_health()
            return

        success, status_msg = self.upload_service.upload_hourly_payload(payload)
        self._server_connected = success

        if success:
            # Advance checkpoint so the same window is not uploaded again
            self.last_uploaded_hour = now
            self.gpio_handler.clear_hourly_counts()
            self._last_upload_status = f"{now.strftime('%H:%M')} Manuell: {status_msg}"
        else:
            self.upload_service.save_failed_upload(payload)
            self._last_upload_status = f"{now.strftime('%H:%M')} Manuell fehlgeschlagen: {status_msg}"

    def _try_hourly_upload(self, now: datetime) -> None:
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        if now.minute != 0 or now.second > 5:
            return

        if self.last_uploaded_hour == current_hour:
            return

        payload = self.aggregation_service.build_hourly_payload(
            device_id=self.config.device_id,
            mood_counts=self.gpio_handler.get_hourly_counts(),
            sensor_samples=self.sensor_service.get_hour_samples(),
            now=now,
        )

        if payload is None:
            return

        success, status_msg = self.upload_service.upload_hourly_payload(payload)
        self._last_upload_status = f"{now.strftime('%H:%M')} {status_msg}"
        self._server_connected = success

        if success:
            self.last_uploaded_hour = current_hour
            self.gpio_handler.clear_hourly_counts()
        else:
            self.upload_service.save_failed_upload(payload)


if __name__ == "__main__":
    app = DeviceApp()
    app.run()
