"""
src/domain/telemetry.py
-----------------------
Model telemetrii — rekordy i partie danych pomiarowych.
DARTRIX FLINT EDGE v0.9 RC
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
import statistics


@dataclass
class TelemetryRecord:
    """Pojedynczy rekord telemetryczny."""

    record_id:   str            = field(default_factory=lambda: str(uuid.uuid4()))
    device_id:   str            = "unknown"
    location:    str            = "unknown"
    timestamp:   datetime       = field(default_factory=datetime.now)
    temperature: Optional[float] = None
    humidity:    Optional[float] = None
    pressure:    Optional[float] = None
    co2:         Optional[float] = None
    vibration:   Optional[float] = None
    door_open:   Optional[bool]  = None
    battery_pct: Optional[float] = None
    signal_rssi: Optional[float] = None
    metadata:    Dict[str, Any]  = field(default_factory=dict)
    flags:       List[str]       = field(default_factory=list)

    def add_flag(self, flag: str):
        if flag not in self.flags:
            self.flags.append(flag)

    def is_critical(self) -> bool:
        """Sprawdza czy rekord zawiera wartości krytyczne."""
        if self.temperature is not None and (self.temperature > 8.0 or self.temperature < -25.0):
            return True
        if self.humidity is not None and self.humidity > 95.0:
            return True
        if self.battery_pct is not None and self.battery_pct < 10.0:
            return True
        return False

    def to_dict(self) -> Dict:
        return {
            "record_id":   self.record_id,
            "device_id":   self.device_id,
            "location":    self.location,
            "timestamp":   self.timestamp.isoformat(),
            "temperature": self.temperature,
            "humidity":    self.humidity,
            "pressure":    self.pressure,
            "co2":         self.co2,
            "vibration":   self.vibration,
            "door_open":   self.door_open,
            "battery_pct": self.battery_pct,
            "signal_rssi": self.signal_rssi,
            "metadata":    self.metadata,
            "flags":       self.flags,
            "is_critical": self.is_critical(),
        }

    def __repr__(self):
        return (f"<TelemetryRecord device={self.device_id} "
                f"loc={self.location} "
                f"temp={self.temperature}°C>")


@dataclass
class TelemetryBatch:
    """Partia rekordów telemetrycznych — do przetwarzania zbiorczego."""

    batch_id:  str                  = field(default_factory=lambda: str(uuid.uuid4()))
    records:   List[TelemetryRecord] = field(default_factory=list)
    created_at: datetime             = field(default_factory=datetime.now)
    source:    str                   = "unknown"
    processed: bool                  = False

    def add(self, record: TelemetryRecord):
        self.records.append(record)

    def __len__(self):
        return len(self.records)

    def critical_records(self) -> List[TelemetryRecord]:
        return [r for r in self.records if r.is_critical()]

    def temperature_stats(self) -> Dict:
        temps = [r.temperature for r in self.records if r.temperature is not None]
        if not temps:
            return {"count": 0}
        return {
            "count":  len(temps),
            "mean":   round(statistics.mean(temps), 3),
            "min":    round(min(temps), 3),
            "max":    round(max(temps), 3),
            "stdev":  round(statistics.stdev(temps), 3) if len(temps) > 1 else 0.0,
        }

    def summary(self) -> Dict:
        return {
            "batch_id":        self.batch_id,
            "source":          self.source,
            "total_records":   len(self.records),
            "critical_count":  len(self.critical_records()),
            "processed":       self.processed,
            "created_at":      self.created_at.isoformat(),
            "temperature_stats": self.temperature_stats(),
        }