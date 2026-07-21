"""
src/services/sensorops/sensor_humidity.py
------------------------------------------
SensorOps Humidity — adapter sensora wilgotności.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import random
import math
from typing import List, Optional, Dict
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType


class HumiditySensor:
    """Adapter sensora wilgotności względnej (RH%)."""

    def __init__(self, sensor_id: str, location: str = "unknown",
                 baseline_rh: float = 60.0, noise_std: float = 1.5):
        self.sensor_id    = sensor_id
        self.location     = location
        self.baseline_rh  = baseline_rh
        self.noise_std    = noise_std
        self.readings_count: int = 0
        self.last_reading: Optional[float] = None
        self.is_online: bool = True
        self._sim_time: float = 0.0

    def read(self, raw_value: float = None) -> Signal:
        if not self.is_online:
            raise RuntimeError(f"Sensor {self.sensor_id} is offline")

        self.readings_count += 1
        self._sim_time += 0.1

        value = raw_value if raw_value is not None else self._simulate()
        value = max(0.0, min(100.0, value))
        self.last_reading = value

        return Signal(
            value       = round(value, 2),
            signal_type = SignalType.HUMIDITY,
            source_id   = self.sensor_id,
            unit        = "%RH",
            confidence  = 0.97,
            metadata    = {"location": self.location},
            tags        = ["humidity", self.location],
        )

    def read_batch(self, n: int = 10) -> List[Signal]:
        return [self.read() for _ in range(n)]

    def simulate_condensation_risk(self, n: int = 5) -> List[Signal]:
        """Symuluje ryzyko kondensacji (wilgotność > 90%)."""
        signals = []
        for i in range(n):
            rh = 88.0 + i * 2.5 + random.gauss(0, 0.5)
            signals.append(self.read(rh))
        return signals

    def status(self) -> Dict:
        return {
            "sensor_id":      self.sensor_id,
            "location":       self.location,
            "is_online":      self.is_online,
            "readings_count": self.readings_count,
            "last_reading":   self.last_reading,
            "baseline_rh":    self.baseline_rh,
        }

    def _simulate(self) -> float:
        cycle = math.sin(self._sim_time * 0.08) * 5.0
        noise = random.gauss(0, self.noise_std)
        return self.baseline_rh + cycle + noise