"""
tests/test_wolf.py
-------------------
Testy jednostkowe modułu WolfGuardian.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from domain.signal import Signal, SignalType
from domain.models import Alert, AlertSeverity, SystemState
from services.wolfguardian.wolf_core import WolfGuardian
from services.wolfguardian.wolf_security import SecurityMonitor
from services.wolfguardian.wolf_alerts import AlertManager


def make_signal(value: float = 4.5, stype: SignalType = SignalType.TEMPERATURE,
                source: str = "sensor-001") -> Signal:
    return Signal(value=value, signal_type=stype, source_id=source)


def test_wolf_watch_safe():
    """Test: bezpieczny sygnał przechodzi weryfikację."""
    wolf = WolfGuardian()
    sig = make_signal()
    result = wolf.watch(sig)
    assert result["watched"] == True
    assert result["is_safe"] == True
    print("  ✅ test_wolf_watch_safe")


def test_wolf_replay_detection():
    """Test: replay attack jest wykrywany."""
    wolf = WolfGuardian()
    sig = make_signal()
    wolf.watch(sig)  # Pierwszy raz — OK
    result = wolf.watch(sig)  # Drugi raz — replay
    assert result["is_safe"] == False
    assert result["threats_count"] > 0
    print("  ✅ test_wolf_replay_detection")


def test_wolf_block_source():
    """Test: blokowanie źródła."""
    wolf = WolfGuardian()
    wolf.block_source("bad-sensor", "test")
    assert wolf.security.is_blocked("bad-sensor")
    print("  ✅ test_wolf_block_source")


def test_wolf_unblock_source():
    """Test: odblokowanie źródła."""
    wolf = WolfGuardian()
    wolf.block_source("sensor-x", "test")
    wolf.unblock_source("sensor-x")
    assert not wolf.security.is_blocked("sensor-x")
    print("  ✅ test_wolf_unblock_source")


def test_wolf_auto_block_after_failures():
    """Test: auto-blokada po przekroczeniu limitu prób."""
    wolf = WolfGuardian(max_failed_attempts=3)
    for _ in range(3):
        wolf.security.record_failed_attempt("attacker-001")
    assert wolf.security.is_blocked("attacker-001")
    print("  ✅ test_wolf_auto_block_after_failures")


def test_wolf_receive_alert():
    """Test: przyjmowanie alertu."""
    wolf = WolfGuardian()
    alert = Alert(
        severity = AlertSeverity.ERROR,
        title    = "Test Alert",
        message  = "Test message",
        source   = "test",
    )
    result = wolf.receive_alert(alert)
    assert result["status"] in ("sent", "deduplicated")
    print("  ✅ test_wolf_receive_alert")


def test_wolf_system_state():
    """Test: zmiana stanu systemu."""
    wolf = WolfGuardian()
    wolf.set_system_state(SystemState.DEGRADED)
    assert wolf.system_state == SystemState.DEGRADED
    print("  ✅ test_wolf_system_state")


def test_security_monitor_verify():
    """Test: weryfikacja sygnału przez SecurityMonitor."""
    sec = SecurityMonitor()
    result = sec.verify_signal(
        signal_id = "sig-001",
        source_id = "sensor-001",
        payload   = {"value": 4.5, "type": "temperature"},
        timestamp = datetime.datetime.now(),
    )
    assert result["is_safe"] == True
    assert result["status"] == "ok"
    print("  ✅ test_security_monitor_verify")


def test_alert_manager_dedup():
    """Test: deduplikacja alertów."""
    mgr = AlertManager(dedup_window_seconds=60)
    alert = Alert(severity=AlertSeverity.WARNING, title="Dup Alert",
                  message="msg", source="test")
    r1 = mgr.receive(alert)
    r2 = mgr.receive(alert)
    assert r1["status"] == "sent"
    assert r2["status"] == "deduplicated"
    print("  ✅ test_alert_manager_dedup")


def test_alert_manager_resolve():
    """Test: rozwiązywanie alertu."""
    mgr = AlertManager()
    alert = Alert(severity=AlertSeverity.ERROR, title="Resolve Test",
                  message="msg", source="test")
    mgr.receive(alert)
    success = mgr.resolve(alert.alert_id, "Fixed")
    assert success == True
    assert alert.resolved == True
    print("  ✅ test_alert_manager_resolve")


def run_all():
    print("\n  === WolfGuardian Tests ===")
    test_wolf_watch_safe()
    test_wolf_replay_detection()
    test_wolf_block_source()
    test_wolf_unblock_source()
    test_wolf_auto_block_after_failures()
    test_wolf_receive_alert()
    test_wolf_system_state()
    test_security_monitor_verify()
    test_alert_manager_dedup()
    test_alert_manager_resolve()
    print("  All WolfGuardian tests passed! ✅\n")


if __name__ == "__main__":
    run_all()