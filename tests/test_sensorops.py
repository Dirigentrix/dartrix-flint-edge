"""
tests/test_sensorops.py
------------------------
Testy jednostkowe modułu SensorOps.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from domain.signal import SignalType, SignalStatus
from services.sensorops.sensor_temperature import TemperatureSensor
from services.sensorops.sensor_humidity import HumiditySensor
from services.sensorops.sensor_signal import SignalSensor


def test_temp_sensor_read():
    """Test: odczyt temperatury."""
    sensor = TemperatureSensor("T-001", "room_A", baseline_temp=4.0)
    sig = sensor.read()
    assert sig.signal_type == SignalType.TEMPERATURE
    assert sig.source_id == "T-001"
    assert isinstance(sig.value, float)
    assert sig.unit == "°C"
    print("  ✅ test_temp_sensor_read")


def test_temp_sensor_raw_value():
    """Test: odczyt z podaną wartością."""
    sensor = TemperatureSensor("T-002", "room_B")
    sig = sensor.read(raw_value=7.5)
    assert abs(sig.value - 7.5) < 0.01
    print("  ✅ test_temp_sensor_raw_value")


def test_temp_sensor_batch():
    """Test: odczyt wsadowy."""
    sensor = TemperatureSensor("T-003", "room_C")
    signals = sensor.read_batch(n=5)
    assert len(signals) == 5
    assert all(s.signal_type == SignalType.TEMPERATURE for s in signals)
    print("  ✅ test_temp_sensor_batch")


def test_temp_sensor_excursion():
    """Test: symulacja excursion."""
    sensor = TemperatureSensor("T-004", "room_D", baseline_temp=4.0)
    signals = sensor.simulate_excursion(target_temp=20.0, duration_readings=5)
    assert len(signals) == 5
    # Ostatni odczyt powinien być bliżej target
    assert signals[-1].value > signals[0].value
    print("  ✅ test_temp_sensor_excursion")


def test_temp_sensor_calibration():
    """Test: kalibracja sensora."""
    sensor = TemperatureSensor("T-005", "room_E", baseline_temp=4.0)
    sensor.read()  # Pierwszy odczyt
    sensor.calibrate(reference_temp=5.0)
    assert sensor.calibration_offset != 0.0
    print("  ✅ test_temp_sensor_calibration")


def test_temp_sensor_offline():
    """Test: sensor offline."""
    sensor = TemperatureSensor("T-006", "room_F")
    sensor.go_offline()
    try:
        sensor.read()
        assert False, "Should raise RuntimeError"
    except RuntimeError:
        pass
    sensor.go_online()
    sig = sensor.read()
    assert sig is not None
    print("  ✅ test_temp_sensor_offline")


def test_humidity_sensor_read():
    """Test: odczyt wilgotności."""
    sensor = HumiditySensor("H-001", "room_A", baseline_rh=60.0)
    sig = sensor.read()
    assert sig.signal_type == SignalType.HUMIDITY
    assert 0.0 <= sig.value <= 100.0
    assert sig.unit == "%RH"
    print("  ✅ test_humidity_sensor_read")


def test_humidity_condensation():
    """Test: symulacja ryzyka kondensacji."""
    sensor = HumiditySensor("H-002", "room_B")
    signals = sensor.simulate_condensation_risk(n=5)
    assert len(signals) == 5
    assert all(s.value > 85.0 for s in signals)
    print("  ✅ test_humidity_condensation")


def test_signal_sensor_read():
    """Test: odczyt sygnału RF."""
    sensor = SignalSensor("S-001", "gateway_A", baseline_rssi=-65.0)
    sig = sensor.read()
    assert sig.signal_type == SignalType.SIGNAL_RAW
    assert sig.unit == "dBm"
    assert -120.0 <= sig.value <= 0.0
    print("  ✅ test_signal_sensor_read")


def test_signal_sensor_jamming():
    """Test: symulacja jammingu."""
    sensor = SignalSensor("S-002", "gateway_B")
    signals = sensor.simulate_jamming(n=5)
    assert len(signals) == 5
    assert all(s.value < -90.0 for s in signals)
    print("  ✅ test_signal_sensor_jamming")


def test_signal_quality_labels():
    """Test: etykiety jakości sygnału."""
    sensor = SignalSensor("S-003", "gw")
    assert sensor._quality_label(-55.0) == "excellent"
    assert sensor._quality_label(-75.0) == "fair"
    assert sensor._quality_label(-100.0) == "critical"
    assert sensor._quality_label(None) == "unknown"
    print("  ✅ test_signal_quality_labels")


def run_all():
    print("\n  === SensorOps Tests ===")
    test_temp_sensor_read()
    test_temp_sensor_raw_value()
    test_temp_sensor_batch()
    test_temp_sensor_excursion()
    test_temp_sensor_calibration()
    test_temp_sensor_offline()
    test_humidity_sensor_read()
    test_humidity_condensation()
    test_signal_sensor_read()
    test_signal_sensor_jamming()
    test_signal_quality_labels()
    print("  All SensorOps tests passed! ✅\n")


if __name__ == "__main__":
    run_all()