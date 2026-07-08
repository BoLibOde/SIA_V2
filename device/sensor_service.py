import logging
import os
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
_I2C_CONNECTION_CHECK_HINT = "Hinweis: Prüfe I2C-Verbindung des SCD41 Sensors."

SCD41_I2C_ADDR = 0x62
COMMAND_START_MEASUREMENT = [0x21, 0xB1]
COMMAND_GET_DATA_READY = [0xE4, 0xB8]
COMMAND_READ_MEASUREMENT = [0xEC, 0x05]
COMMAND_STOP_MEASUREMENT = [0x3F, 0x86]
COMMAND_SOFT_RESET = [0x36, 0x82]

# Resilience knobs
_INIT_RETRIES = 5          # max consecutive init failures before evaluating fallback
_MAX_READ_ERRORS = 5       # consecutive read errors that trigger a hardware-session restart
_INIT_RETRY_DELAY = 2.0    # seconds between init attempts
_REINIT_DELAY = 2.0        # seconds before restarting after read-error recovery
_RECOVERY_CHECK_INTERVAL = 5.0  # seconds between hardware recovery checks in simulation fallback

# Plausibility bounds for raw SCD41 output
_CO2_MIN_PPM = 350
_CO2_MAX_PPM = 5000
_TEMP_MIN_C = -20.0
_TEMP_MAX_C = 65.0
_HUMIDITY_MIN_PCT = 0.0
_HUMIDITY_MAX_PCT = 100.0


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
    if calculate_crc(response[0:2]) != response[2]:
        raise ValueError("CRC mismatch on data-ready response")
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

    if not (_CO2_MIN_PPM <= co2 <= _CO2_MAX_PPM):
        raise ValueError(f"Implausible CO2: {co2} ppm")
    if not (_TEMP_MIN_C <= temp <= _TEMP_MAX_C):
        raise ValueError(f"Implausible temperature: {temp:.2f} °C")
    if not (_HUMIDITY_MIN_PCT <= humidity <= _HUMIDITY_MAX_PCT):
        raise ValueError(f"Implausible humidity: {humidity:.2f} %")

    return co2, temp, humidity


class SensorService:
    def __init__(
        self,
        read_interval_seconds: int = 5,
        simulation_mode: bool = False,
        enable_simulation_fallback: bool = False,
        max_samples: int = 720,
    ) -> None:
        self.read_interval_seconds = max(1, int(read_interval_seconds))
        self.simulation_mode = simulation_mode
        self.enable_simulation_fallback = enable_simulation_fallback
        self.max_samples = max(10, int(max_samples))

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_reading: Optional[SensorReading] = None
        self.readings: list[SensorReading] = []
        self.lock = threading.Lock()

        self._sim_temp = 22.0
        self._sim_humidity = 45.0
        self._sim_co2 = 500
        self._simulated_active = False
        self._hardware_active = False

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

    def discard_samples_before(self, cutoff: datetime) -> None:
        """Remove all buffered samples with a timestamp earlier than *cutoff*.

        Called after a successful 15-minute aggregate upload so that the
        discarded samples cannot appear in a later upload window.
        """
        with self.lock:
            self.readings = [r for r in self.readings if r.timestamp >= cutoff]

    def is_simulated(self) -> bool:
        with self.lock:
            return self._simulated_active

    def is_hardware_active(self) -> bool:
        with self.lock:
            return self._hardware_active

    def has_data(self) -> bool:
        with self.lock:
            return self.latest_reading is not None

    def get_status_text(self) -> str:
        return "OK" if self.has_data() else "FEHLER"

    def _append_reading(self, reading: SensorReading) -> None:
        with self.lock:
            self.latest_reading = reading
            self.readings.append(reading)
            if len(self.readings) > self.max_samples:
                del self.readings[0:len(self.readings) - self.max_samples]

    def _set_mode_flags(self, *, hardware_active: bool, simulated_active: bool) -> None:
        with self.lock:
            self._hardware_active = hardware_active
            self._simulated_active = simulated_active

    def _detect_scd41_bus(self, log_attempts: bool = True) -> Optional[int]:
        """Detektiert welcher I2C-Bus der SCD41 Sensor angeschlossen ist.

        Versucht Bus 0, 1 und 2 (Standard auf Raspberry Pi).
        Prüft zuerst ob die Devices existieren (/dev/i2c-X) um System-Fehler zu vermeiden.
        Sendet einen einfachen Daten-Ready-Check um zu prüfen ob der Sensor antwortet.
        """
        available_buses = [bus_id for bus_id in (0, 1, 2) if os.path.exists(f"/dev/i2c-{bus_id}")]

        if not available_buses:
            _LOG.error(
                "Keine I2C-Devices gefunden (/dev/i2c-0, /dev/i2c-1, /dev/i2c-2). "
                "Prüfe ob I2C aktiviert ist (raspi-config)."
            )
            return None

        for bus_id in available_buses:
            attempt_log = _LOG.info if log_attempts else _LOG.debug
            attempt_log(
                "I2C-Bus Auto-Detektion: Versuche Bus %d für SCD41 (Adresse 0x%02X)",
                bus_id,
                SCD41_I2C_ADDR,
            )
            try:
                with SMBus(bus_id) as bus:
                    bus.write_i2c_block_data(
                        SCD41_I2C_ADDR,
                        COMMAND_GET_DATA_READY[0],
                        COMMAND_GET_DATA_READY[1:],
                    )
                    time.sleep(0.01)
                _LOG.info("SCD41 auf Bus %d gefunden (Adresse 0x%02X)", bus_id, SCD41_I2C_ADDR)
                return bus_id
            except Exception as error:
                error_log = _LOG.warning if log_attempts else _LOG.debug
                error_log(
                    "SCD41 auf Bus %d nicht erreichbar (Adresse 0x%02X): %s. "
                    "%s",
                    bus_id,
                    SCD41_I2C_ADDR,
                    error,
                    _I2C_CONNECTION_CHECK_HINT,
                )
        return None

    def _run_simulation_with_recovery(self) -> bool:
        self._set_mode_flags(hardware_active=False, simulated_active=True)
        next_recovery_check = 0.0
        while self.running:
            self._append_reading(self._simulated_read())
            now = time.monotonic()
            if now >= next_recovery_check:
                bus_id = self._detect_scd41_bus(log_attempts=False)
                if bus_id is not None:
                    _LOG.info("SCD41 Hardware wiederhergestellt - Wechsel zu echten Sensoren (Bus %d)", bus_id)
                    self._set_mode_flags(hardware_active=False, simulated_active=False)
                    return True
                next_recovery_check = now + _RECOVERY_CHECK_INTERVAL
            time.sleep(self.read_interval_seconds)
        return False

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
        init_failures = 0
        self._set_mode_flags(hardware_active=False, simulated_active=False)

        while self.running:
            if init_failures >= _INIT_RETRIES:
                _LOG.error(
                    "SCD41 Hardware fehlgeschlagen nach %d Versuchen",
                    _INIT_RETRIES,
                )
                if self.enable_simulation_fallback:
                    _LOG.warning("Fallback auf Simulation aktiviert")
                    recovered = self._run_simulation_with_recovery()
                    if recovered:
                        init_failures = 0
                        continue
                    return
                _LOG.warning("Simulation-Fallback deaktiviert - Sensor bleibt ohne Daten, Hardware wird weiter geprüft")
                init_failures = 0

            if init_failures > 0:
                time.sleep(_INIT_RETRY_DELAY)

            read_restart = False
            bus_id = self._detect_scd41_bus()
            if bus_id is None:
                init_failures += 1
                continue
            try:
                with SMBus(bus_id) as bus:
                    # Stop any in-progress measurement before resetting
                    try:
                        bus.write_i2c_block_data(
                            SCD41_I2C_ADDR,
                            COMMAND_STOP_MEASUREMENT[0],
                            COMMAND_STOP_MEASUREMENT[1:],
                        )
                        time.sleep(0.5)
                    except OSError as _stop_err:
                        _LOG.debug("SCD41 pre-reset stop failed (ignored): %s", _stop_err)

                    bus.write_i2c_block_data(
                        SCD41_I2C_ADDR,
                        COMMAND_SOFT_RESET[0],
                        COMMAND_SOFT_RESET[1:],
                    )
                    time.sleep(1.0)

                    bus.write_i2c_block_data(
                        SCD41_I2C_ADDR,
                        COMMAND_START_MEASUREMENT[0],
                        COMMAND_START_MEASUREMENT[1:],
                    )
                    time.sleep(5.0)

                    _LOG.info(
                        "SCD41 hardware mode initialized successfully on bus %d (Adresse 0x%02X)",
                        bus_id,
                        SCD41_I2C_ADDR,
                    )
                    init_failures = 0
                    self._set_mode_flags(hardware_active=True, simulated_active=False)

                    consecutive_errors = 0
                    while self.running:
                        try:
                            if _is_data_ready(bus, SCD41_I2C_ADDR):
                                co2, temp, humidity = _read_measurement(bus, SCD41_I2C_ADDR)
                                self._append_reading(
                                    SensorReading(
                                        temperature_c=round(temp, 2),
                                        humidity_pct=round(humidity, 2),
                                        co2_ppm=int(co2),
                                        timestamp=datetime.now(UTC),
                                    )
                                )
                            consecutive_errors = 0
                        except Exception as error:
                            consecutive_errors += 1
                            _LOG.warning(
                                "SCD41 read failed (%d/%d) on bus %d (Adresse 0x%02X): %s. "
                                "%s",
                                consecutive_errors,
                                _MAX_READ_ERRORS,
                                bus_id,
                                SCD41_I2C_ADDR,
                                error,
                                _I2C_CONNECTION_CHECK_HINT,
                            )
                            if consecutive_errors >= _MAX_READ_ERRORS:
                                _LOG.warning(
                                    "Too many consecutive SCD41 read errors, restarting hardware session"
                                )
                                self._set_mode_flags(hardware_active=False, simulated_active=False)
                                read_restart = True
                                break

                        time.sleep(self.read_interval_seconds)

                    try:
                        bus.write_i2c_block_data(
                            SCD41_I2C_ADDR,
                            COMMAND_STOP_MEASUREMENT[0],
                            COMMAND_STOP_MEASUREMENT[1:],
                        )
                    except OSError as _stop_err:
                        _LOG.debug("SCD41 post-loop stop failed (ignored): %s", _stop_err)

            except Exception as error:
                self._set_mode_flags(hardware_active=False, simulated_active=False)
                init_failures += 1
                _LOG.warning(
                    "SCD41 init attempt %d/%d failed on bus %d (Adresse 0x%02X): %s. "
                    "%s",
                    init_failures,
                    _INIT_RETRIES,
                    bus_id,
                    SCD41_I2C_ADDR,
                    error,
                    _I2C_CONNECTION_CHECK_HINT,
                )

            if read_restart and self.running:
                time.sleep(_REINIT_DELAY)

    def _loop(self) -> None:
        if self.simulation_mode:
            _LOG.info("Simulationsmodus explizit aktiviert (CLI/ENV Überschreibung)")
            self._set_mode_flags(hardware_active=False, simulated_active=True)
            while self.running:
                self._append_reading(self._simulated_read())
                time.sleep(self.read_interval_seconds)
            return

        if not SMBUS2_AVAILABLE:
            _LOG.error("`smbus2` ist nicht verfügbar. Echte Sensoren können nicht gelesen werden.")
            self._set_mode_flags(hardware_active=False, simulated_active=False)
            while self.running:
                time.sleep(self.read_interval_seconds)
            return

        self._hardware_loop()
