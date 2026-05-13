import time
from datetime import datetime

from device.config import DeviceConfig
from device.gpio_handler import GpioHandler
from device.sensor_service import SensorService


class DeviceApp:
    def __init__(self) -> None:
        self.config = DeviceConfig()
        self.sensor_service = SensorService(read_interval_seconds=self.config.sensor_interval_seconds)
        self.gpio_handler = GpioHandler(
            good_pin=self.config.good_button_pin,
            neutral_pin=self.config.neutral_button_pin,
            bad_pin=self.config.bad_button_pin,
        )
        self.running = False

    def run(self) -> None:
        self.running = True
        self.sensor_service.start()
        self.gpio_handler.start()

        print(f"[{datetime.now().isoformat()}] Device app started")
        print(f"Display: {self.config.display_width}x{self.config.display_height}")

        try:
            while self.running:
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

                time.sleep(self.config.ui_refresh_seconds)
        except KeyboardInterrupt:
            print("Stopping device app...")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        self.sensor_service.stop()
        self.gpio_handler.stop()


if __name__ == "__main__":
    app = DeviceApp()
    app.run()
