"""
demos/cold_chain_demo.py
-------------------------
Demo Cold Chain — symulacja łańcucha chłodniczego.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from services.sensorops.sensor_temperature import TemperatureSensor
from services.sensorops.sensor_humidity import HumiditySensor


def run_demo(app=None):
    """Uruchamia demo Cold Chain."""
    print("\n" + "═"*60)
    print("  🧊 COLD CHAIN DEMO — Farmaceutyki (2–8°C)")
    print("═"*60)

    # Inicjalizacja sensorów
    temp_sensor = TemperatureSensor("TEMP-PHARMA-01", "pharma_storage",
                                    baseline_temp=4.5, noise_std=0.2)
    hum_sensor  = HumiditySensor("HUM-PHARMA-01", "pharma_storage",
                                  baseline_rh=55.0, noise_std=1.0)

    if app is None:
        # Standalone mode
        from src.app import DartrixFlintEdge
        from infrastructure.config import SystemConfig
        app = DartrixFlintEdge(SystemConfig.development())
        app.start()

    print("\n  Phase 1: Normal operation (10 readings)")
    print("  " + "─"*50)
    for i in range(10):
        sig = temp_sensor.read()
        result = app.process_signal(sig, "pharma-device-01")
        status = "✅" if not result["is_anomaly"] else "⚠️ "
        print(f"  {status} T={result['value']:6.2f}°C | "
              f"risk={result['risk_score']:.3f} | "
              f"level={result['risk_level']}")

    print("\n  Phase 2: Temperature excursion (door left open)")
    print("  " + "─"*50)
    excursion = temp_sensor.simulate_excursion(target_temp=18.0, duration_readings=8)
    for sig in excursion:
        result = app.process_signal(sig, "pharma-device-01")
        status = "🔴" if result["is_anomaly"] else "✅"
        print(f"  {status} T={result['value']:6.2f}°C | "
              f"risk={result['risk_score']:.3f} | "
              f"⚡ {result['decision'][:45]}")

    print("\n  Phase 3: Recovery (door closed)")
    print("  " + "─"*50)
    temp_sensor.baseline_temp = 4.5  # Reset
    for i in range(5):
        sig = temp_sensor.read()
        result = app.process_signal(sig, "pharma-device-01")
        status = "✅" if not result["is_anomaly"] else "⚠️ "
        print(f"  {status} T={result['value']:6.2f}°C | "
              f"risk={result['risk_score']:.3f} | "
              f"Recovering...")

    # Compliance report
    print("\n  📋 Compliance Report:")
    print("  " + "─"*50)
    report = app.flint_temp.compliance_report()
    print(f"  Profile:      {report['profile_range']}")
    print(f"  Total reads:  {report['total_readings']}")
    print(f"  In range:     {report['in_range']}")
    print(f"  Compliance:   {report['compliance_pct']}%")
    print(f"  Compliant:    {'✅ YES' if report['compliant'] else '❌ NO'}")
    if report.get("mkt"):
        print(f"  MKT:          {report['mkt']}°C")
    print(f"  Excursions:   {report['excursions_total']}")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_demo()