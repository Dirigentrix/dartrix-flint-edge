"""
demos/replay_attack_demo.py
----------------------------
Demo Replay Attack — symulacja ataku i detekcji przez WolfGuardian.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os, time, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from domain.signal import Signal, SignalType
from services.sensorops.sensor_signal import SignalSensor


def run_demo(app=None):
    """Uruchamia demo ataku replay."""
    print("\n" + "═"*60)
    print("  🛡️  REPLAY ATTACK DEMO — WolfGuardian Security")
    print("═"*60)

    if app is None:
        from src.app import DartrixFlintEdge
        from infrastructure.config import SystemConfig
        app = DartrixFlintEdge(SystemConfig.development())
        app.start()

    sig_sensor = SignalSensor("SIG-001", "gateway_A", baseline_rssi=-65.0)

    print("\n  Phase 1: Legitimate signals")
    print("  " + "─"*50)
    legitimate_signals = []
    for i in range(5):
        sig = sig_sensor.read()
        legitimate_signals.append(sig)
        result = app.process_signal(sig, "gateway-01")
        print(f"  ✅ Signal {sig.signal_id[:8]} | "
              f"RSSI={sig.value:.1f}dBm | "
              f"safe={result['is_safe']}")

    print("\n  Phase 2: Replay attack (replaying old signals)")
    print("  " + "─"*50)
    for sig in legitimate_signals[:3]:
        # Replay: same signal_id, old timestamp
        result = app.process_signal(sig, "gateway-01")
        threat = "🔴 REPLAY DETECTED" if not result["is_safe"] else "✅ OK"
        print(f"  {threat} | Signal {sig.signal_id[:8]} | "
              f"threats={result.get('threats_count', 0)}")

    print("\n  Phase 3: Signal jamming simulation")
    print("  " + "─"*50)
    jamming_signals = sig_sensor.simulate_jamming(n=5)
    for sig in jamming_signals:
        result = app.process_signal(sig, "gateway-01")
        quality = sig.metadata.get("quality", "unknown")
        print(f"  📡 RSSI={sig.value:.1f}dBm | "
              f"quality={quality} | "
              f"risk={result['risk_score']:.3f}")

    print("\n  Phase 4: Brute force (multiple failed attempts)")
    print("  " + "─"*50)
    attacker_id = "attacker-999"
    for i in range(7):
        app.wolf.security.record_failed_attempt(attacker_id)
        blocked = app.wolf.security.is_blocked(attacker_id)
        status = "🔒 BLOCKED" if blocked else f"  Attempt {i+1}"
        print(f"  {status} | source={attacker_id}")

    # Security report
    print("\n  🔐 Security Report:")
    print("  " + "─"*50)
    report = app.wolf.security.security_report()
    print(f"  Threats detected:  {report['threats_detected']}")
    print(f"  Sources blocked:   {report['sources_blocked']}")
    print(f"  Signals verified:  {report['signals_verified']}")
    print(f"  Blocked sources:   {report['blocked_sources']}")
    print(f"  Threats by type:   {report['threats_by_type']}")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_demo()