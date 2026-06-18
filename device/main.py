import time
from datetime import UTC, datetime

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
        self.last_uploaded_period_end: datetime | None = None

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
                now = datetime.now(UTC)
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
                    self._set_upload_status(now, "Tageszähler zurückgesetzt")

                status_updated = self.ui.action_upload or self.ui.action_reset_daily

                # Live-event track: upload one measurement per button press so
                # the website reflects mood changes without waiting for the next
                # hourly sensor aggregate window.
                live_events = self.gpio_handler.pop_live_events()
                if live_events:
                    if latest is None:
                        self.gpio_handler.requeue_live_events(live_events)
                        self._set_upload_status(now, f"Live wartet: {len(live_events)} ohne Sensordaten")
                        status_updated = True
                    else:
                        for mood in live_events:
                            success, status_msg = self.upload_service.upload_live_event(mood, latest, now)
                            self._server_connected = success
                            if success:
                                self._set_upload_status(now, f"Live: {mood} {status_msg}")
                            else:
                                self._set_upload_status(
                                    now,
                                    f"Live fehlgeschlagen (gepuffert): {mood} {status_msg}",
                                )
                            status_updated = True

                retried_count, remaining_count = self.upload_service.retry_pending_uploads()
                if (retried_count or remaining_count) and not status_updated:
                    self._set_upload_status(now, f"Retry: {retried_count} gesendet, {remaining_count} offen")
                self._try_periodic_sensor_upload(now)

                # Refresh server connection status every ~30 loop ticks
                health_check_counter += 1
                if health_check_counter >= 30:
                    self._server_connected = self.upload_service.check_server_health()
                    health_check_counter = 0

                self.ui.draw(latest, daily_counts, self._server_connected, self._last_upload_status)

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


if __name__ == "__main__":
    app = DeviceApp()
    app.run()
