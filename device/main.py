import time
from datetime import datetime

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
                hourly_counts = self.gpio_handler.get_hourly_counts()

                if not self.ui.handle_events():
                    self.running = False
                    break

                self.ui.draw(latest, hourly_counts, self._server_connected, self._last_upload_status)
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

