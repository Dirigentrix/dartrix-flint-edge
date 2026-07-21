"""
src/domain/signal.py
--------------------
Model sygnału — reprezentuje surowe dane z sensorów.
DARTRIX FLINT EDGE v0.9 RC
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


class SignalType(Enum):
    """Typy sygnałów obsługiwanych przez system."""
    TEMPERATURE      = "temperature"
    HUMIDITY         = "humidity"
    PRESSURE         = "pressure"
    SIGNAL_RAW       = "signal_raw"
    SIGNAL_PROCESSED = "signal_processed"
    DARPIN_BINDING   = "darpin_binding"
    SPION_TRAJECTORY = "spion_trajectory"
    CO2              = "co2"
    VIBRATION        = "vibration"
    DOOR_OPEN        = "door_open"


class SignalStatus(Enum):
    """Status przetwarzania sygnału."""
    RAW       = "raw"
    VALIDATED = "validated"
    PROCESSED = "processed"
    ANOMALY   = "anomaly"
    REJECTED  = "rejected"


@dataclass
class Signal:
    """Reprezentacja pojedynczego sygnału z sensora."""

    value:       float
    signal_type: SignalType
    timestamp:   datetime          = field(default_factory=datetime.now)
    source_id:   str               = field(default_factory=lambda: str(uuid.uuid4())[:8])
    signal_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    status:      SignalStatus      = SignalStatus.RAW
    metadata:    Dict[str, Any]    = field(default_factory=dict)
    unit:        str               = ""
    confidence:  float             = 1.0
    raw_data:    Optional[Dict]    = None
    tags:        List[str]         = field(default_factory=list)

    def validate(self) -> bool:
        """Waliduje poprawność sygnału."""
        if not isinstance(self.value, (int, float)):
            return False
        if not (0.0 <= self.confidence <= 1.0):
            return False
        return True

    def mark_anomaly(self, reason: str = ""):
        self.status = SignalStatus.ANOMALY
        self.metadata["anomaly_reason"] = reason

    def to_dict(self) -> Dict:
        return {
            "signal_id":   self.signal_id,
            "source_id":   self.source_id,
            "value":       self.value,
            "signal_type": self.signal_type.value,
            "timestamp":   self.timestamp.isoformat(),
            "status":      self.status.value,
            "metadata":    self.metadata,
            "unit":        self.unit,
            "confidence":  self.confidence,
            "tags":        self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Signal":
        return cls(
            signal_id   = data.get("signal_id", str(uuid.uuid4())),
            source_id   = data.get("source_id", "unknown"),
            value       = float(data["value"]),
            signal_type = SignalType(data["signal_type"]),
            timestamp   = datetime.fromisoformat(data["timestamp"])
                          if "timestamp" in data else datetime.now(),
            status      = SignalStatus(data.get("status", "raw")),
            metadata    = data.get("metadata", {}),
            unit        = data.get("unit", ""),
            confidence  = float(data.get("confidence", 1.0)),
            tags        = data.get("tags", []),
        )

    def __repr__(self):
        return (f"<Signal [{self.signal_type.value}] "
                f"val={self.value}{self.unit} "
                f"status={self.status.value}>")