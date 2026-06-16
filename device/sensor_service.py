import logging
import random
import threading
import time
from datetime import UTC, datetime
from typing import Optional

from device.models import SensorReading

try:
    from smbus2 import SMBus
    SMBUS2_AVAILABLE = True
except Exception:
    SMBUS2_AVAILABLE = False
    SMBus = None


_LOG = logging.getLogger(__name__)

SCD41_I2C_ADDR = 0x62
COMMAND_START_MEASUREMENT = [0x21, 0xB1]
COMMAND_GET_DATA_READY = [0xE4, 0xB8]
COMMAND_READ_MEASUREMENT = [0xEC, 0x05]
COMMAND_STOP_MEASUREMENT = [0x3F, 0x86]
COMMAND_SOFT_RESET = [0x36, 0x82]


def calculate_crc(data: list[int]) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc <<= 1
    return crc & 0xFF


def _is_data_ready(bus: SMBus, address: int) -> bool:
    bus.write_i2c_block_data(address, COMMAND_GET_DATA_READY[0], COMMAND_GET_DATA_READY[1:])
    time.sleep(0.005)
    response = bus.read_i2c_block_data(address, 0x00, 3)
    word = (response[0] << 8) | response[1]
    return word != 0


def _read_measurement(bus: SMBus, address: int) -> tuple[int, float, float]:
    bus.write_i2c_block_data(address, COMMAND_READ_MEASUREMENT[0], COMMAND_READ_MEASUREMENT[1:])
    time.sleep(0.005)
    data = bus.read_i2c_block_data(address, 0x00, 9)

    for i in range(3):
        word_bytes = data[i * 3:i * 3 + 2]
        crc = data[i * 3 + 2]
        if calculate_crc(word_bytes) != crc:
            raise ValueError("CRC mismatch on measurement field")

    co2 = int.from_bytes(bytes(data[0:2]), "big")
    temp_raw = int.from_bytes(bytes(data[3:5]), "big")
    humidity_raw = int.from_bytes(bytes(data[6:8]), "big")

    temp = -45 + (175 * temp_raw) / 65535.0
    humidity = 100 * humidity_raw / 65535.0
    return co2, temp, humidity


class SensorService:
    def __init__(self, read_interval_seconds: int = 5, simulation_mode: bool = False, max_samples: int = 720) -> None:
        self.read_interval_seconds = max(1, int(read_interval_seconds))
        self.simulation_mode = simulation_mode
        self.max_samples = max(10, int(max_samples))

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_reading: Optional[SensorReading] = None
        self.readings: list[SensorReading] = []
        self.lock = threading.Lock()

        self._sim_temp = 22.0
        self._sim_humidity = 45.0
        self._sim_co2 = 500

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2)

    def get_latest_reading(self) -> Optional[SensorReading]:
        with self.lock:
            return self.latest_reading

    def get_hour_samples(self) -> list[SensorReading]:
        with self.lock:
            return list(self.readings)

    def _append_reading(self, reading: SensorReading) -> None:
        with self.lock:
            self.latest_reading = reading
            self.readings.append(reading)
            if len(self.readings) > self.max_samples:
                del self.readings[0:len(self.readings) - self.max_samples]

    def _simulated_read(self) -> SensorReading:
        self._sim_temp += random.uniform(-0.15, 0.15)
        self._sim_humidity += random.uniform(-0.4, 0.4)
        self._sim_co2 += int(random.uniform(-15, 20))

        self._sim_humidity = max(0.0, min(100.0, self._sim_humidity))
        self._sim_co2 = max(400, min(5000, self._sim_co2))

        return SensorReading(
            temperature_c=round(self._sim_temp, 2),
            humidity_pct=round(self._sim_humidity, 2),
            co2_ppm=int(self._sim_co2),
            timestamp=datetime.now(UTC),
        )

    def _hardware_loop(self) -> None:
        try:
            with SMBus(1) as bus:
                bus.write_i2c_block_data(SCD41_I2C_ADDR, COMMAND_SOFT_RESET[0], COMMAND_SOFT_RESET[1:])
                time.sleep(1.0)

                bus.write_i2c_block_data(SCD41_I2C_ADDR, COMMAND_START_MEASUREMENT[0], COMMAND_START_MEASUREMENT[1:])
                time.sleep(5.0)

                while self.running:
                    try:
                        if _is_data_ready(bus, SCD41_I2C_ADDR):
                            co2, temp, humidity = _read_measurement(bus, SCD41_I2C_ADDR)
                            reading = SensorReading(
                                temperature_c=round(temp, 2),
                                humidity_pct=round(humidity, 2),
                                co2_ppm=int(co2),
                                timestamp=datetime.now(UTC),
                            )
                            self._append_reading(reading)
                    except Exception as error:
                        _LOG.warning("SCD41 read failed: %s", error)

                    time.sleep(self.read_interval_seconds)

                try:
                    bus.write_i2c_block_data(SCD41_I2C_ADDR, COMMAND_STOP_MEASUREMENT[0], COMMAND_STOP_MEASUREMENT[1:])
                except Exception:
                    pass
        except Exception as error:
            _LOG.warning("SCD41 hardware mode failed, switching to simulation: %s", error)
            while self.running:
                self._append_reading(self._simulated_read())
                time.sleep(self.read_interval_seconds)

    def _loop(self) -> None:
        if self.simulation_mode or not SMBUS2_AVAILABLE:
            if not SMBUS2_AVAILABLE and not self.simulation_mode:
                _LOG.warning("smbus2 not available, using simulation mode")
            while self.running:
                self._append_reading(self._simulated_read())
                time.sleep(self.read_interval_seconds)
            return

        self._hardware_loop()
