import time
from datetime import datetime

from device.aggregation_service import AggregationService
from device.config import DeviceConfig
from device.gpio_handler import GpioHandler
from device.sensor_service import SensorService
from device.upload_service import UploadService


class DeviceApp:
    def __init__(self) -> None:
        self.config = DeviceConfig()
        self.sensor_service = SensorService(read_interval_seconds=self.config.sensor_interval_seconds)
        self.gpio_handler = GpioHandler(
            good_pin=self.config.good_button_pin,
            neutral_pin=self.config.neutral_button_pin,
            bad_pin=self.config.bad_button_pin,
        )
        self.aggregation_service = AggregationService()
        self.upload_service = UploadService(
            server_base_url=self.config.server_base_url,
            upload_endpoint=self.config.upload_endpoint,
        )
        self.running = False
        self.last_uploaded_hour: datetime | None = None

    def run(self) -> None:
        self.running = True
        self.sensor_service.start()
        self.gpio_handler.start()

        print(f"[{datetime.now().isoformat()}] Device app started")
        print(f"Display: {self.config.display_width}x{self.config.display_height}")

        try:
            while self.running:
                now = datetime.utcnow()
                latest = self.sensor_service.get_latest_reading()
                counts = self.gpio_handler.get_counts()

                if latest is not None:
                    print(
                        f"Temp: {latest.temperature_c:.1f} C | "
                        f"Humidity: {latest.humidity_pct:.1f} % | "
                        f"CO2: {latest.co2_ppm} ppm | "
                        f"Counts: good={counts.good}, neutral={counts.neutral}, bad={counts.bad}"
                    )
                else:
                    print(
                        f"No sensor data yet | "
                        f"Counts: good={counts.good}, neutral={counts.neutral}, bad={counts.bad}"
                    )

                self._try_hourly_upload(now)
                time.sleep(self.config.ui_refresh_seconds)
        except KeyboardInterrupt:
            print("Stopping device app...")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        self.sensor_service.stop()
        self.gpio_handler.stop()

    def _try_hourly_upload(self, now: datetime) -> None:
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        if now.minute != 0 or now.second > 5:
            return

        if self.last_uploaded_hour == current_hour:
            return

        payload = self.aggregation_service.build_hourly_payload(
            device_id=self.config.device_id,
            mood_counts=self.gpio_handler.get_counts(),
            sensor_samples=self.sensor_service.get_hour_samples(),
            now=now,
        )

        if payload is None:
            return

        success = self.upload_service.upload_hourly_payload(payload)
        if success:
            self.last_uploaded_hour = current_hour
            print(f"Uploaded hourly payload for {current_hour.isoformat()}")
        else:
            print("Hourly upload failed")


if __name__ == "__main__":
    app = DeviceApp()
    app.run()
