"""
src/app.py
----------
DARTRIX FLINT EDGE v0.9 RC — Główny punkt wejścia aplikacji.
Integruje: FLINT + TES + WolfGuardian + SensorOps + Infrastructure.

Uruchomienie:
    python src/app.py
    python src/app.py --env production
    python src/app.py --demo cold_chain
"""

import sys
import os
import datetime
import argparse
from typing import Dict, List

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.signal import Signal, SignalType
from domain.models import SystemState, RiskLevel
from services.flint.flint_core import FlintCore
from services.flint.flint_temperature import FlintTemperature
from services.flint.flint_signal import FlintSignal
from services.tes.tes_engine import TESEngine
from services.wolfguardian.wolf_core import WolfGuardian
from services.sensorops.sensor_temperature import TemperatureSensor
from services.sensorops.sensor_humidity import HumiditySensor
from services.sensorops.sensor_signal import SignalSensor
from infrastructure.config import SystemConfig
from infrastructure.logging import SystemLogger, LogLevel
from infrastructure.storage import DataStorage


class DartrixFlintEdge:
    """
    Główna klasa aplikacji DARTRIX FLINT EDGE.
    Orkiestruje wszystkie moduły systemu.
    """

    VERSION = "0.9-RC"
    BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🟦 DARTRIX FLINT EDGE v0.9 RC                      ║
║          Modularna platforma telemetryczno-decyzyjna         ║
║          FLINT · TES · WolfGuardian · SensorOps             ║
╚══════════════════════════════════════════════════════════════╝
"""

    def __init__(self, config: SystemConfig = None):
        self.config  = config or SystemConfig.development()
        self.logger  = SystemLogger("dartrix", LogLevel.INFO)
        self.storage = DataStorage()

        # Inicjalizacja modułów
        self.flint       = FlintCore(
            window_size = self.config.flint.window_size,
            sensitivity = self.config.flint.sensitivity,
        )
        self.flint_temp  = FlintTemperature(self.config.flint.temp_profile)
        self.flint_sig   = FlintSignal()
        self.tes         = TESEngine(self.config.tes.auto_execute)
        self.wolf        = WolfGuardian(
            auto_block          = self.config.wolf.auto_block,
            max_failed_attempts = self.config.wolf.max_failed_attempts,
        )

        self.started_at  = datetime.datetime.now()
        self.is_running  = False
        self.tick_count  = 0

    # ── LIFECYCLE ─────────────────────────────────────────────

    def start(self):
        """Uruchamia system."""
        print(self.BANNER)
        self.logger.info(f"DARTRIX FLINT EDGE {self.VERSION} starting...",
                         {"env": self.config.environment})
        self.wolf.set_system_state(SystemState.RUNNING)
        self.is_running = True
        self.storage.store_event("system_start", {"version": self.VERSION})
        self.logger.info("All modules initialized. System READY.")

    def stop(self):
        """Zatrzymuje system."""
        self.is_running = False
        self.wolf.set_system_state(SystemState.SHUTDOWN)
        self.storage.store_event("system_stop", {"ticks": self.tick_count})
        self.logger.info(f"System stopped after {self.tick_count} ticks.")

    # ── PIPELINE ──────────────────────────────────────────────

    def process_signal(self, signal: Signal,
                       device_id: str = "unknown") -> Dict:
        """
        Przetwarza sygnał przez pełny pipeline:
        SensorOps → FLINT → TES → WolfGuardian → Storage
        """
        self.tick_count += 1

        # 1. WolfGuardian — weryfikacja bezpieczeństwa
        watch_result = self.wolf.watch(signal)

        if not watch_result["is_safe"]:
            self.logger.warning(
                f"Unsafe signal from {signal.source_id}",
                {"threats": watch_result["threats_count"]}
            )

        # 2. FLINT — analiza anomalii
        flint_result = self.flint.process(signal)

        # 3. FLINT Temperature (jeśli temperatura)
        temp_result = None
        if signal.signal_type == SignalType.TEMPERATURE:
            temp_result = self.flint_temp.analyze(signal, device_id)

        # 4. TES — decyzja
        context = {
            **flint_result,
            "device_id":   device_id,
            "is_safe":     watch_result["is_safe"],
        }
        if signal.signal_type == SignalType.TEMPERATURE:
            context["temperature"] = signal.value
            context["temp_min"]    = self.flint_temp.profile["min"]
            context["temp_max"]    = self.flint_temp.profile["max"]
        elif signal.signal_type == SignalType.HUMIDITY:
            context["humidity"] = signal.value

        decision = self.tes.evaluate(context, source_module="app_pipeline")

        # 5. Route alerts from TES to WolfGuardian
        for alert in self.tes.get_active_alerts()[-3:]:
            pass  # Already handled by TES

        # 6. Storage
        self.storage.store_signal(signal.to_dict())
        self.storage.store_decision(decision.to_dict())

        return {
            "tick":         self.tick_count,
            "signal_id":    signal.signal_id,
            "signal_type":  signal.signal_type.value,
            "value":        signal.value,
            "is_safe":      watch_result["is_safe"],
            "is_anomaly":   flint_result["is_anomaly"],
            "risk_score":   flint_result["risk_score"],
            "risk_level":   flint_result["risk_level"],
            "decision":     decision.recommendation,
            "temp_result":  temp_result,
        }

    def process_batch(self, signals: list,
                      device_id: str = "unknown") -> list:
        """Przetwarza listę sygnałów."""
        return [self.process_signal(s, device_id) for s in signals]

    # ── STATUS ────────────────────────────────────────────────

    def status(self) -> Dict:
        """Zwraca pełny status systemu."""
        uptime = (datetime.datetime.now() - self.started_at).total_seconds()
        return {
            "system":      "DARTRIX FLINT EDGE",
            "version":     self.VERSION,
            "environment": self.config.environment,
            "is_running":  self.is_running,
            "tick_count":  self.tick_count,
            "uptime_sec":  round(uptime, 1),
            "modules": {
                "flint":       self.flint.stats(),
                "flint_temp":  self.flint_temp.stats(),
                "flint_signal": self.flint_sig.stats(),
                "tes":         self.tes.stats(),
                "wolf":        self.wolf.stats(),
            },
            "storage":     self.storage.stats(),
        }

    def print_status(self):
        """Drukuje status systemu."""
        s = self.status()
        print(f"\n{'─'*60}")
        print(f"  DARTRIX FLINT EDGE {s['version']} | {s['environment'].upper()}")
        print(f"  Uptime: {s['uptime_sec']:.0f}s | Ticks: {s['tick_count']}")
        print(f"  FLINT: {s['modules']['flint']['signals_processed']} signals, "
              f"{s['modules']['flint']['anomalies_detected']} anomalies")
        print(f"  TES:   {s['modules']['tes']['decisions_count']} decisions")
        print(f"  Wolf:  {s['modules']['wolf']['signals_watched']} watched, "
              f"{s['modules']['wolf']['security']['threats_detected']} threats")
        print(f"{'─'*60}\n")


# ── TYPE HINT FIX ─────────────────────────────────────────────



# ── ENTRY POINT ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="DARTRIX FLINT EDGE v0.9 RC")
    parser.add_argument("--env",  default="development",
                        choices=["development", "production"])
    parser.add_argument("--demo", default="basic",
                        choices=["basic", "cold_chain", "security"])
    args = parser.parse_args()

    # Config
    if args.env == "production":
        config = SystemConfig.production()
    else:
        config = SystemConfig.development()

    # App
    app = DartrixFlintEdge(config)
    app.start()

    # Run demo
    if args.demo == "cold_chain":
        from demos.cold_chain_demo import run_demo
        run_demo(app)
    elif args.demo == "security":
        from demos.replay_attack_demo import run_demo
        run_demo(app)
    else:
        _basic_demo(app)

    app.print_status()
    app.stop()


def _basic_demo(app: DartrixFlintEdge):
    """Podstawowe demo — kilka sygnałów przez pipeline."""
    print("\n  Running basic demo...\n")

    sensor_t = TemperatureSensor("TEMP-001", "cold_room_A", baseline_temp=4.0)
    sensor_h = HumiditySensor("HUM-001", "cold_room_A", baseline_rh=65.0)

    # Normalne odczyty
    for i in range(5):
        sig = sensor_t.read()
        result = app.process_signal(sig, "device-001")
        print(f"  T={result['value']:.2f}°C | "
              f"anomaly={result['is_anomaly']} | "
              f"risk={result['risk_score']:.3f} | "
              f"{result['decision'][:50]}")

    # Symulacja excursion
    print("\n  Simulating temperature excursion...\n")
    excursion_signals = sensor_t.simulate_excursion(target_temp=15.0, duration_readings=5)
    for sig in excursion_signals:
        result = app.process_signal(sig, "device-001")
        print(f"  T={result['value']:.2f}°C | "
              f"anomaly={result['is_anomaly']} | "
              f"risk={result['risk_score']:.3f} | "
              f"⚠️  {result['decision'][:50]}")


if __name__ == "__main__":
    main()