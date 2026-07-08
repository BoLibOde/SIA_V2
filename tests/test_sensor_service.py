"""Unit tests for device/sensor_service.py.

Tests cover:
- CRC calculation
- _is_data_ready: CRC validation of data-ready response
- _read_measurement: CRC validation and plausibility checks
- SensorService._hardware_loop: init retries, optional simulation fallback, session restart, recovery
"""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from device.models import SensorReading
from device.sensor_service import (
    _CO2_MAX_PPM,
    _CO2_MIN_PPM,
    _INIT_RETRIES,
    _MAX_READ_ERRORS,
    _TEMP_MAX_C,
    SensorService,
    _is_data_ready,
    _read_measurement,
    calculate_crc,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _data_ready_response(word: int) -> list[int]:
    """Build a valid 3-byte data-ready response for the given 16-bit word."""
    high, low = (word >> 8) & 0xFF, word & 0xFF
    return [high, low, calculate_crc([high, low])]


def _encoded_word(raw: int) -> list[int]:
    """Encode a 16-bit value as [high, low, crc]."""
    high, low = (raw >> 8) & 0xFF, raw & 0xFF
    return [high, low, calculate_crc([high, low])]


def _temp_raw(temp_c: float) -> int:
    return max(0, min(65535, int((temp_c + 45) / 175 * 65535)))


def _humidity_raw(pct: float) -> int:
    return max(0, min(65535, int(pct / 100 * 65535)))


def _measurement_frame(co2: int, temp_c: float, humidity_pct: float) -> list[int]:
    """Build a valid 9-byte SCD41 measurement frame."""
    return (
        _encoded_word(co2)
        + _encoded_word(_temp_raw(temp_c))
        + _encoded_word(_humidity_raw(humidity_pct))
    )


# ---------------------------------------------------------------------------
# calculate_crc
# ---------------------------------------------------------------------------

def test_calculate_crc_known_value() -> None:
    # Sensirion CRC-8 example: [0xBE, 0xEF] → 0x92
    assert calculate_crc([0xBE, 0xEF]) == 0x92


def test_calculate_crc_is_deterministic() -> None:
    data = [0x12, 0x34]
    assert calculate_crc(data) == calculate_crc(data)


# ---------------------------------------------------------------------------
# _is_data_ready
# ---------------------------------------------------------------------------

def test_is_data_ready_returns_true_when_data_available() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _data_ready_response(0x0001)
    assert _is_data_ready(bus, 0x62) is True


def test_is_data_ready_returns_false_when_not_ready() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _data_ready_response(0x0000)
    assert _is_data_ready(bus, 0x62) is False


def test_is_data_ready_raises_on_crc_mismatch() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = [0x00, 0x01, 0xFF]  # wrong CRC
    with pytest.raises(ValueError, match="CRC mismatch"):
        _is_data_ready(bus, 0x62)


# ---------------------------------------------------------------------------
# _read_measurement
# ---------------------------------------------------------------------------

def test_read_measurement_returns_plausible_values() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _measurement_frame(1080, 31.07, 41.61)
    co2, temp, humidity = _read_measurement(bus, 0x62)
    assert 1070 <= co2 <= 1090
    assert 30.5 <= temp <= 31.7
    assert 41.0 <= humidity <= 42.5


def test_read_measurement_raises_on_crc_mismatch() -> None:
    bus = MagicMock()
    frame = _measurement_frame(1080, 31.0, 40.0)
    frame[2] ^= 0xFF  # corrupt first CRC byte
    bus.read_i2c_block_data.return_value = frame
    with pytest.raises(ValueError, match="CRC mismatch"):
        _read_measurement(bus, 0x62)


def test_read_measurement_rejects_co2_too_high() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _measurement_frame(_CO2_MAX_PPM + 100, 25.0, 50.0)
    with pytest.raises(ValueError, match="Implausible CO2"):
        _read_measurement(bus, 0x62)


def test_read_measurement_rejects_co2_too_low() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _measurement_frame(_CO2_MIN_PPM - 1, 25.0, 50.0)
    with pytest.raises(ValueError, match="Implausible CO2"):
        _read_measurement(bus, 0x62)


def test_read_measurement_rejects_temperature_too_high() -> None:
    bus = MagicMock()
    bus.read_i2c_block_data.return_value = _measurement_frame(1000, _TEMP_MAX_C + 10.0, 50.0)
    with pytest.raises(ValueError, match="Implausible temperature"):
        _read_measurement(bus, 0x62)


# ---------------------------------------------------------------------------
# SensorService._hardware_loop
# ---------------------------------------------------------------------------

_I2C_DETECTION_BUSES = 2

@patch("device.sensor_service.time.sleep")
def test_hardware_loop_falls_back_to_simulation_after_all_retries(mock_sleep) -> None:
    """After _INIT_RETRIES consecutive SMBus failures the service falls back to simulation."""
    service = SensorService(
        read_interval_seconds=1,
        simulation_mode=False,
        enable_simulation_fallback=True,
    )
    service.running = True
    smbus_calls = 0

    class _FailSMBus:
        def __init__(self, bus_id: int) -> None:
            nonlocal smbus_calls
            smbus_calls += 1
            raise OSError("I2C not accessible")

    # Patch _simulated_read to stop the loop after the first simulated reading.
    original_sim = service._simulated_read

    def _stop_on_sim():
        service.running = False
        return original_sim()

    service._simulated_read = _stop_on_sim

    _available = {f"/dev/i2c-{b}" for b in range(_I2C_DETECTION_BUSES)}
    with (
        patch("device.sensor_service.os.path.exists", side_effect=lambda p: p in _available),
        patch("device.sensor_service.SMBus", _FailSMBus),
    ):
        service._hardware_loop()

    expected_calls = (_INIT_RETRIES * _I2C_DETECTION_BUSES) + _I2C_DETECTION_BUSES
    assert smbus_calls == expected_calls
    assert service.get_latest_reading() is not None  # simulation produced a reading


@patch("device.sensor_service.time.sleep")
def test_hardware_loop_retries_after_single_init_failure(mock_sleep) -> None:
    """A single transient init failure must NOT cause permanent simulation fallback."""
    service = SensorService(read_interval_seconds=1, simulation_mode=False)
    service.running = True
    smbus_calls = 0
    sim_calls = 0
    original_sim = service._simulated_read

    class _FailOnceSMBus:
        def __init__(self, bus_id: int) -> None:
            nonlocal smbus_calls
            smbus_calls += 1
            if smbus_calls == 1:
                raise OSError("Transient I2C error")
            # Second attempt: stop the service so the read loop exits cleanly.
            service.running = False
            raise OSError("Stop test")

    def _count_sim():
        nonlocal sim_calls
        sim_calls += 1
        return original_sim()

    service._simulated_read = _count_sim

    _available = {f"/dev/i2c-{b}" for b in range(_I2C_DETECTION_BUSES)}
    with (
        patch("device.sensor_service.os.path.exists", side_effect=lambda p: p in _available),
        patch("device.sensor_service.SMBus", _FailOnceSMBus),
    ):
        service._hardware_loop()

    assert smbus_calls == 2  # retried after the first failure
    assert sim_calls == 0    # never fell back to simulation


@patch("device.sensor_service.time.sleep")
def test_hardware_loop_without_fallback_keeps_no_data_after_retries(mock_sleep) -> None:
    service = SensorService(
        read_interval_seconds=1,
        simulation_mode=False,
        enable_simulation_fallback=False,
    )
    service.running = True
    smbus_calls = 0
    sleep_calls = 0

    class _FailSMBus:
        def __init__(self, bus_id: int) -> None:
            nonlocal smbus_calls
            smbus_calls += 1
            raise OSError("I2C not accessible")

    def _counted_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= _INIT_RETRIES + 2:
            service.running = False

    mock_sleep.side_effect = _counted_sleep

    _available = {f"/dev/i2c-{b}" for b in range(_I2C_DETECTION_BUSES)}
    with (
        patch("device.sensor_service.os.path.exists", side_effect=lambda p: p in _available),
        patch("device.sensor_service.SMBus", _FailSMBus),
    ):
        service._hardware_loop()

    assert smbus_calls >= _INIT_RETRIES
    assert service.get_latest_reading() is None
    assert service.has_data() is False
    assert service.is_simulated() is False


@patch("device.sensor_service.time.sleep")
def test_hardware_loop_restarts_session_on_repeated_read_errors(mock_sleep) -> None:
    """After _MAX_READ_ERRORS consecutive read errors the hardware session is restarted."""
    service = SensorService(read_interval_seconds=1, simulation_mode=False)
    service.running = True

    session_count = 0
    # A bus whose reads always fail (init writes succeed).
    failing_bus = MagicMock()
    failing_bus.read_i2c_block_data.side_effect = OSError("read error")

    class _SessionCountingSMBus:
        def __init__(self, bus_id: int) -> None:
            nonlocal session_count
            session_count += 1
            if session_count >= 2:
                # Stop the service so the outer loop can exit cleanly.
                service.running = False
                raise OSError("second session init fails to stop test")

        def __enter__(self):
            return failing_bus

        def __exit__(self, *args):
            return False

    with (
        patch.object(service, "_detect_scd41_bus", return_value=1),
        patch("device.sensor_service.SMBus", _SessionCountingSMBus),
    ):
        service._hardware_loop()

    assert session_count == 2  # session was restarted once after read errors
    assert failing_bus.read_i2c_block_data.call_count == _MAX_READ_ERRORS


@patch("device.sensor_service.time.sleep")
def test_hardware_loop_can_recover_from_simulation_to_hardware(mock_sleep) -> None:
    service = SensorService(
        read_interval_seconds=1,
        simulation_mode=False,
        enable_simulation_fallback=True,
    )
    service.running = True
    bus = MagicMock()

    class _OkSMBus:
        def __init__(self, bus_id: int) -> None:
            pass

        def __enter__(self):
            return bus

        def __exit__(self, *args):
            return False

    detect_sequence = [None] * _INIT_RETRIES + [1]

    def _fake_data_ready(_bus, _addr):
        service.running = False
        return True

    with (
        patch.object(service, "_detect_scd41_bus", side_effect=detect_sequence),
        patch.object(service, "_run_simulation_with_recovery", return_value=True),
        patch("device.sensor_service.SMBus", _OkSMBus),
        patch("device.sensor_service._is_data_ready", side_effect=_fake_data_ready),
        patch("device.sensor_service._read_measurement", return_value=(615, 21.5, 41.0)),
    ):
        service._hardware_loop()

    assert service.has_data() is True
    assert service.get_latest_reading() is not None
    assert service.is_hardware_active() is True


def test_status_text_reports_error_without_data_and_ok_with_data() -> None:
    service = SensorService(read_interval_seconds=1, simulation_mode=True)
    assert service.get_status_text() == "FEHLER"

    service._append_reading(_measurement_to_reading(615, 21.5, 41.0))
    assert service.has_data() is True
    assert service.get_status_text() == "OK"


def _measurement_to_reading(co2: int, temp_c: float, humidity_pct: float) -> SensorReading:
    return SensorReading(
        temperature_c=temp_c,
        humidity_pct=humidity_pct,
        co2_ppm=co2,
        timestamp=datetime.now(UTC),
    )
