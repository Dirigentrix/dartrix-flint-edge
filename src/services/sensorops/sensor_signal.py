"""
src/services/sensorops/sensor_signal.py
----------------------------------------
SensorOps Signal — adapter sensora sygnału RF/komunikacyjnego.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import random
from typing import List, Optional, Dict
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType


class SignalSensor:
    """Adapter sensora sygnału RF (RSSI, SNR, jakość łącza)."""

    def __init__(self, sensor_id: str, location: str = "unknown",
                 baseline_rssi: float = -65.0, noise_std: float = 3.0):
        self.sensor_id      = sensor_id
        self.location       = location
        self.baseline_rssi  = baseline_rssi
        self.noise_std      = noise_std
        self.readings_count: int = 0
        self.last_rssi: Optional[float] = None
        self.is_online: bool = True
        self.packet_loss_pct: float = 0.0

    def read(self, raw_rssi: float = None) -> Signal:
        if not self.is_online:
            raise RuntimeError(f"Sensor {self.sensor_id} is offline")

        self.readings_count += 1
        rssi = raw_rssi if raw_rssi is not None else self._simulate_rssi()
        rssi = max(-120.0, min(0.0, rssi))
        self.last_rssi = rssi

        return Signal(
            value       = round(rssi, 2),
            signal_type = SignalType.SIGNAL_RAW,
            source_id   = self.sensor_id,
            unit        = "dBm",
            confidence  = self._confidence(rssi),
            metadata    = {
                "location":        self.location,
                "packet_loss_pct": self.packet_loss_pct,
                "quality":         self._quality_label(rssi),
            },
            tags = ["signal", "rssi", self.location],
        )

    def read_batch(self, n: int = 10) -> List[Signal]:
        return [self.read() for _ in range(n)]

    def simulate_jamming(self, n: int = 5) -> List[Signal]:
        """Symuluje zakłócenia sygnału."""
        signals = []
        for _ in range(n):
            rssi = random.uniform(-110, -95)
            signals.append(self.read(rssi))
        return signals

    def status(self) -> Dict:
        return {
            "sensor_id":       self.sensor_id,
            "location":        self.location,
            "is_online":       self.is_online,
            "readings_count":  self.readings_count,
            "last_rssi":       self.last_rssi,
            "packet_loss_pct": self.packet_loss_pct,
            "quality":         self._quality_label(self.last_rssi) if self.last_rssi else "unknown",
        }

    def _simulate_rssi(self) -> float:
        noise = random.gauss(0, self.noise_std)
        fade = random.uniform(-5, 2)
        return self.baseline_rssi + noise + fade

    def _confidence(self, rssi: float) -> float:
        if rssi >= -70:   return 0.99
        if rssi >= -80:   return 0.95
        if rssi >= -90:   return 0.85
        if rssi >= -100:  return 0.70
        return 0.50

    def _quality_label(self, rssi: Optional[float]) -> str:
        if rssi is None:    return "unknown"
        if rssi >= -60:     return "excellent"
        if rssi >= -70:     return "good"
        if rssi >= -80:     return "fair"
        if rssi >= -90:     return "poor"
        return "critical"