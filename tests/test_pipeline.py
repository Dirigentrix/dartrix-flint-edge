"""
tests/test_pipeline.py
-----------------------
Testy integracyjne — pełny pipeline DARTRIX FLINT EDGE.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from src.app import DartrixFlintEdge
from infrastructure.config import SystemConfig
from services.sensorops.sensor_temperature import TemperatureSensor
from services.sensorops.sensor_humidity import HumiditySensor
from services.sensorops.sensor_signal import SignalSensor
from domain.signal import Signal, SignalType


def make_app(env: str = "development") -> DartrixFlintEdge:
    cfg = SystemConfig.development() if env == "development" else SystemConfig.production()
    app = DartrixFlintEdge(cfg)
    app.start()
    return app


def test_pipeline_normal_signal():
    """Test: normalny sygnał przechodzi przez pipeline."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-01", "test_room", baseline_temp=4.5)
    sig = sensor.read()
    result = app.process_signal(sig, "device-test")
    assert "tick" in result
    assert "is_anomaly" in result
    assert "risk_score" in result
    assert "decision" in result
    assert result["tick"] == 1
    print("  ✅ test_pipeline_normal_signal")
    app.stop()


def test_pipeline_excursion():
    """Test: excursion jest wykrywany w pipeline."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-02", "test_room", baseline_temp=4.5)
    excursion = sensor.simulate_excursion(target_temp=20.0, duration_readings=5)
    anomalies = 0
    for sig in excursion:
        result = app.process_signal(sig, "device-test")
        if result["is_anomaly"]:
            anomalies += 1
    assert anomalies > 0
    print(f"  ✅ test_pipeline_excursion ({anomalies}/5 anomalies detected)")
    app.stop()


def test_pipeline_batch():
    """Test: przetwarzanie wsadowe."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-03", "test_room")
    signals = sensor.read_batch(n=10)
    results = app.process_batch(signals, "device-batch")
    assert len(results) == 10
    assert all("tick" in r for r in results)
    print("  ✅ test_pipeline_batch")
    app.stop()


def test_pipeline_humidity():
    """Test: sygnał wilgotności przez pipeline."""
    app = make_app()
    sensor = HumiditySensor("H-PIPE-01", "test_room", baseline_rh=65.0)
    sig = sensor.read()
    result = app.process_signal(sig, "device-hum")
    assert result["signal_type"] == "humidity"
    print("  ✅ test_pipeline_humidity")
    app.stop()


def test_pipeline_security_replay():
    """Test: replay attack jest blokowany w pipeline."""
    app = make_app()
    sig = Signal(value=4.5, signal_type=SignalType.TEMPERATURE, source_id="sensor-replay")
    # Pierwszy odczyt
    r1 = app.process_signal(sig, "device-replay")
    # Replay
    r2 = app.process_signal(sig, "device-replay")
    assert r1["is_safe"] == True
    assert r2["is_safe"] == False
    print("  ✅ test_pipeline_security_replay")
    app.stop()


def test_pipeline_storage():
    """Test: dane są zapisywane w storage."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-04", "test_room")
    for _ in range(5):
        sig = sensor.read()
        app.process_signal(sig, "device-storage")
    stats = app.storage.stats()
    assert stats["stored_counts"]["signals"] == 5
    assert stats["stored_counts"]["decisions"] == 5
    print("  ✅ test_pipeline_storage")
    app.stop()


def test_pipeline_status():
    """Test: status systemu jest kompletny."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-05", "test_room")
    for _ in range(3):
        app.process_signal(sensor.read(), "device-status")
    status = app.status()
    assert status["tick_count"] == 3
    assert "modules" in status
    assert "flint" in status["modules"]
    assert "tes" in status["modules"]
    assert "wolf" in status["modules"]
    print("  ✅ test_pipeline_status")
    app.stop()


def test_pipeline_compliance_report():
    """Test: raport compliance po przetworzeniu sygnałów."""
    app = make_app()
    sensor = TemperatureSensor("T-PIPE-06", "pharma_room", baseline_temp=5.0)
    for _ in range(20):
        app.process_signal(sensor.read(), "pharma-device")
    report = app.flint_temp.compliance_report()
    assert report["total_readings"] == 20
    assert "compliance_pct" in report
    print(f"  ✅ test_pipeline_compliance_report (compliance={report['compliance_pct']}%)")
    app.stop()


def run_all():
    print("\n  === Pipeline Integration Tests ===")
    test_pipeline_normal_signal()
    test_pipeline_excursion()
    test_pipeline_batch()
    test_pipeline_humidity()
    test_pipeline_security_replay()
    test_pipeline_storage()
    test_pipeline_status()
    test_pipeline_compliance_report()
    print("  All Pipeline tests passed! ✅\n")


if __name__ == "__main__":
    run_all()