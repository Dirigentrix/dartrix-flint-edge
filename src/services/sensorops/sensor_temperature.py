"""
src/services/sensorops/sensor_temperature.py
---------------------------------------------
SensorOps Temperature — symulator i adapter sensora temperatury.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import random
import math
from typing import List, Dict, Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType, SignalStatus


class TemperatureSensor:
    """
    Adapter sensora temperatury.
    Obsługuje: odczyt, kalibrację, symulację, walidację.
    """

    def __init__(self, sensor_id: str, location: str = "unknown",
                 baseline_temp: float = 4.0, noise_std: float = 0.3):
        self.sensor_id     = sensor_id
        self.location      = location
        self.baseline_temp = baseline_temp
        self.noise_std     = noise_std
        self.calibration_offset: float = 0.0
        self.readings_count: int = 0
        self.last_reading: Optional[float] = None
        self.last_read_at: Optional[datetime.datetime] = None
        self.is_online: bool = True
        self.battery_pct: float = 100.0
        self._sim_time: float = 0.0

    def read(self, raw_value: float = None) -> Signal:
        """
        Odczytuje temperaturę.
        Jeśli raw_value=None, generuje symulowaną wartość.
        """
        if not self.is_online:
            raise RuntimeError(f"Sensor {self.sensor_id} is offline")

        self.readings_count += 1
        self._sim_time += 0.1
        self.battery_pct = max(0.0, self.battery_pct - 0.001)

        if raw_value is None:
            value = self._simulate()
        else:
            value = raw_value + self.calibration_offset

        self.last_reading = value
        self.last_read_at = datetime.datetime.now()

        return Signal(
            value       = round(value, 3),
            signal_type = SignalType.TEMPERATURE,
            source_id   = self.sensor_id,
            unit        = "°C",
            confidence  = self._confidence(),
            metadata    = {
                "location":    self.location,
                "battery_pct": round(self.battery_pct, 2),
                "calibration": self.calibration_offset,
            },
            tags = ["temperature", self.location],
        )

    def read_batch(self, n: int = 10,
                   interval_seconds: float = 60.0) -> List[Signal]:
        """Generuje serię odczytów."""
        signals = []
        for i in range(n):
            sig = self.read()
            sig.timestamp = datetime.datetime.now() - datetime.timedelta(
                seconds=(n - i) * interval_seconds
            )
            signals.append(sig)
        return signals

    def calibrate(self, reference_temp: float):
        """Kalibruje sensor względem wartości referencyjnej."""
        if self.last_reading is not None:
            self.calibration_offset = reference_temp - (self.last_reading - self.calibration_offset)

    def simulate_excursion(self, target_temp: float = 15.0,
                           duration_readings: int = 10) -> List[Signal]:
        """Symuluje przekroczenie temperatury."""
        signals = []
        for i in range(duration_readings):
            progress = i / duration_readings
            temp = self.baseline_temp + (target_temp - self.baseline_temp) * progress
            temp += random.gauss(0, self.noise_std)
            sig = self.read(temp)
            signals.append(sig)
        return signals

    def go_offline(self):
        self.is_online = False

    def go_online(self):
        self.is_online = True

    def status(self) -> Dict:
        return {
            "sensor_id":          self.sensor_id,
            "location":           self.location,
            "is_online":          self.is_online,
            "battery_pct":        round(self.battery_pct, 2),
            "readings_count":     self.readings_count,
            "last_reading":       self.last_reading,
            "last_read_at":       self.last_read_at.isoformat() if self.last_read_at else None,
            "calibration_offset": self.calibration_offset,
            "baseline_temp":      self.baseline_temp,
        }

    def _simulate(self) -> float:
        """Symuluje odczyt z szumem i oscylacją dobową."""
        daily_cycle = math.sin(self._sim_time * 0.1) * 0.5
        noise = random.gauss(0, self.noise_std)
        return self.baseline_temp + daily_cycle + noise + self.calibration_offset

    def _confidence(self) -> float:
        """Oblicza pewność odczytu na podstawie stanu baterii."""
        if self.battery_pct > 50:
            return 0.99
        elif self.battery_pct > 20:
            return 0.95
        elif self.battery_pct > 5:
            return 0.85
        return 0.70