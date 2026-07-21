"""
src/services/flint/flint_temperature.py
----------------------------------------
FLINT Temperature — specjalizowany moduł analizy temperatury.
Kluczowy dla Cold Chain (łańcuch chłodniczy).
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import statistics
from typing import List, Dict, Optional, Tuple
from collections import deque
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType, SignalStatus
from domain.models import RiskLevel, Alert, AlertSeverity


class ColdChainProfile:
    """Profil wymagań temperaturowych dla Cold Chain."""

    PROFILES = {
        "frozen":       {"min": -25.0, "max": -15.0, "label": "Mrożone"},
        "deep_frozen":  {"min": -30.0, "max": -18.0, "label": "Głęboko mrożone"},
        "chilled":      {"min": 0.0,   "max": 4.0,   "label": "Schłodzone"},
        "pharma":       {"min": 2.0,   "max": 8.0,   "label": "Farmaceutyki"},
        "fresh":        {"min": 0.0,   "max": 7.0,   "label": "Świeże"},
        "ambient":      {"min": 15.0,  "max": 25.0,  "label": "Otoczenie"},
    }

    @classmethod
    def get(cls, profile_name: str) -> Dict:
        return cls.PROFILES.get(profile_name, cls.PROFILES["chilled"])

    @classmethod
    def list_profiles(cls) -> List[str]:
        return list(cls.PROFILES.keys())


class TemperatureExcursion:
    """Rejestr przekroczenia temperatury (excursion)."""

    def __init__(self, device_id: str, profile: str):
        self.excursion_id = f"EXC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.device_id = device_id
        self.profile = profile
        self.started_at = datetime.datetime.now()
        self.ended_at: Optional[datetime.datetime] = None
        self.peak_temp: float = 0.0
        self.readings: List[float] = []
        self.active = True

    def add_reading(self, temp: float):
        self.readings.append(temp)
        if abs(temp) > abs(self.peak_temp):
            self.peak_temp = temp

    def close(self):
        self.active = False
        self.ended_at = datetime.datetime.now()

    @property
    def duration_minutes(self) -> float:
        end = self.ended_at or datetime.datetime.now()
        return round((end - self.started_at).total_seconds() / 60, 2)

    @property
    def mean_excursion_temp(self) -> float:
        return round(statistics.mean(self.readings), 3) if self.readings else 0.0

    def to_dict(self) -> Dict:
        return {
            "excursion_id":       self.excursion_id,
            "device_id":          self.device_id,
            "profile":            self.profile,
            "started_at":         self.started_at.isoformat(),
            "ended_at":           self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes":   self.duration_minutes,
            "peak_temp":          self.peak_temp,
            "mean_excursion_temp": self.mean_excursion_temp,
            "readings_count":     len(self.readings),
            "active":             self.active,
        }


class FlintTemperature:
    """
    Specjalizowany moduł analizy temperatury dla Cold Chain.
    Śledzi excursions, oblicza MKT (Mean Kinetic Temperature),
    generuje raporty zgodności.
    """

    def __init__(self, profile: str = "pharma"):
        self.profile_name = profile
        self.profile = ColdChainProfile.get(profile)
        self.excursions: List[TemperatureExcursion] = []
        self._current_excursion: Optional[TemperatureExcursion] = None
        self._history: deque = deque(maxlen=1000)
        self.readings_count: int = 0
        self.alerts: List[Alert] = []

    def analyze(self, signal: Signal, device_id: str = "unknown") -> Dict:
        """Analizuje sygnał temperatury."""
        if signal.signal_type != SignalType.TEMPERATURE:
            return {"error": "Not a temperature signal"}

        self.readings_count += 1
        temp = signal.value
        self._history.append({"temp": temp, "ts": signal.timestamp.isoformat()})

        min_t = self.profile["min"]
        max_t = self.profile["max"]
        in_range = min_t <= temp <= max_t

        # Excursion tracking
        excursion_info = self._track_excursion(temp, device_id, in_range)

        # Risk score
        if in_range:
            risk_score = 0.0
            risk_level = RiskLevel.NONE
        else:
            deviation = max(min_t - temp, temp - max_t, 0)
            allowed_range = max_t - min_t
            risk_score = min(1.0, deviation / max(1, allowed_range))
            risk_level = RiskLevel.from_score(risk_score)

        # Alert
        alert = None
        if not in_range and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            alert = Alert(
                severity = AlertSeverity.CRITICAL if risk_level == RiskLevel.CRITICAL else AlertSeverity.ERROR,
                title    = f"Temperature Excursion [{self.profile_name}]",
                message  = (f"Device {device_id}: {temp}°C "
                            f"(allowed: {min_t}–{max_t}°C)"),
                source   = "flint_temperature",
                tags     = ["temperature", "cold_chain", self.profile_name],
            )
            self.alerts.append(alert)

        return {
            "device_id":    device_id,
            "temperature":  temp,
            "profile":      self.profile_name,
            "in_range":     in_range,
            "allowed_min":  min_t,
            "allowed_max":  max_t,
            "risk_score":   round(risk_score, 4),
            "risk_level":   risk_level.label,
            "excursion":    excursion_info,
            "alert":        alert.to_dict() if alert else None,
            "mkt":          self.calculate_mkt(),
            "ts":           signal.timestamp.isoformat(),
        }

    def calculate_mkt(self) -> Optional[float]:
        """
        Oblicza Mean Kinetic Temperature (MKT) — farmaceutyczny standard.
        MKT = -Ea/R / ln(Σexp(-Ea/RT_i) / n)
        Ea = 83.144 kJ/mol (standardowa energia aktywacji)
        R  = 8.314 J/(mol·K)
        """
        import math
        temps = [r["temp"] for r in self._history]
        if len(temps) < 2:
            return None
        Ea = 83144.0  # J/mol
        R  = 8.314    # J/(mol·K)
        try:
            sum_exp = sum(math.exp(-Ea / (R * (t + 273.15))) for t in temps)
            mkt_k = -Ea / (R * math.log(sum_exp / len(temps)))
            return round(mkt_k - 273.15, 3)
        except (ValueError, ZeroDivisionError):
            return None

    def compliance_report(self) -> Dict:
        """Raport zgodności Cold Chain."""
        temps = [r["temp"] for r in self._history]
        if not temps:
            return {"status": "no_data"}

        in_range = [t for t in temps
                    if self.profile["min"] <= t <= self.profile["max"]]
        compliance_pct = round(len(in_range) / len(temps) * 100, 2)

        return {
            "profile":          self.profile_name,
            "profile_range":    f"{self.profile['min']}–{self.profile['max']}°C",
            "total_readings":   len(temps),
            "in_range":         len(in_range),
            "out_of_range":     len(temps) - len(in_range),
            "compliance_pct":   compliance_pct,
            "compliant":        compliance_pct >= 95.0,
            "mkt":              self.calculate_mkt(),
            "excursions_total": len(self.excursions),
            "active_excursion": self._current_excursion is not None,
            "temp_stats": {
                "mean": round(statistics.mean(temps), 3),
                "min":  round(min(temps), 3),
                "max":  round(max(temps), 3),
            } if temps else {},
        }

    def _track_excursion(self, temp: float, device_id: str,
                         in_range: bool) -> Optional[Dict]:
        if not in_range:
            if self._current_excursion is None:
                self._current_excursion = TemperatureExcursion(device_id, self.profile_name)
                self.excursions.append(self._current_excursion)
            self._current_excursion.add_reading(temp)
            return self._current_excursion.to_dict()
        else:
            if self._current_excursion is not None:
                self._current_excursion.close()
                self._current_excursion = None
        return None

    def stats(self) -> Dict:
        return {
            "module":           "FLINT Temperature",
            "profile":          self.profile_name,
            "readings_count":   self.readings_count,
            "excursions_total": len(self.excursions),
            "active_excursion": self._current_excursion is not None,
            "active_alerts":    len([a for a in self.alerts if not a.resolved]),
            "compliance":       self.compliance_report(),
        }