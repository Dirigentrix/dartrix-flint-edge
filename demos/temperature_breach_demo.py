"""
demos/temperature_breach_demo.py
---------------------------------
Demo Temperature Breach — analiza przekroczenia temperatury z MKT.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from services.sensorops.sensor_temperature import TemperatureSensor, ColdChainProfile


def run_demo(app=None):
    """Uruchamia demo analizy przekroczenia temperatury."""
    print("\n" + "═"*60)
    print("  🌡️  TEMPERATURE BREACH DEMO — MKT Analysis")
    print("═"*60)

    if app is None:
        from src.app import DartrixFlintEdge
        from infrastructure.config import SystemConfig
        app = DartrixFlintEdge(SystemConfig.development())
        app.start()

    print("\n  Available Cold Chain Profiles:")
    for name, profile in ColdChainProfile.PROFILES.items():
        print(f"    {name:15s}: {profile['min']}°C to {profile['max']}°C  ({profile['label']})")

    print("\n  Testing 'pharma' profile (2–8°C):")
    print("  " + "─"*50)

    sensor = TemperatureSensor("TEMP-MKT-01", "pharma_vault",
                               baseline_temp=5.0, noise_std=0.15)

    # Scenario: gradual warming
    scenarios = [
        ("Normal",    5.0,  10),
        ("Warming",   10.0,  8),
        ("Hot",       20.0,  5),
        ("Recovery",  5.0,   8),
    ]

    for scenario_name, target, n_readings in scenarios:
        print(f"\n  [{scenario_name}] target={target}°C, readings={n_readings}")
        sensor.baseline_temp = target
        for _ in range(n_readings):
            sig = sensor.read()
            result = app.process_signal(sig, "pharma-vault-01")
            icon = "🔴" if result["is_anomaly"] else "✅"
            print(f"    {icon} {sig.value:6.2f}°C | "
                  f"risk={result['risk_score']:.3f} | "
                  f"{result['risk_level']}")

    # Final MKT report
    print("\n  📊 MKT & Compliance Analysis:")
    print("  " + "─"*50)
    report = app.flint_temp.compliance_report()
    print(f"  Total readings:   {report['total_readings']}")
    print(f"  In range:         {report['in_range']} ({report['compliance_pct']}%)")
    print(f"  Out of range:     {report['out_of_range']}")
    print(f"  Compliant (≥95%): {'✅ YES' if report['compliant'] else '❌ NO'}")
    if report.get("mkt"):
        print(f"  MKT:              {report['mkt']}°C")
        mkt_ok = report["mkt"] <= 8.0
        print(f"  MKT in range:     {'✅ YES' if mkt_ok else '❌ NO'}")
    print(f"  Excursions:       {report['excursions_total']}")
    if report.get("temp_stats"):
        ts = report["temp_stats"]
        print(f"  Temp stats:       mean={ts['mean']}°C, "
              f"min={ts['min']}°C, max={ts['max']}°C")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_demo()