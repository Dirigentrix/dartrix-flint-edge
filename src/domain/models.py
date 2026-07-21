"""
src/domain/models.py
--------------------
Wspólne modele domenowe — enumeracje i typy pomocnicze.
DARTRIX FLINT EDGE v0.9 RC
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


class RiskLevel(Enum):
    """Poziomy ryzyka systemowego."""
    NONE     = (0, "Brak",     "#10B981")
    LOW      = (1, "Niski",    "#3B82F6")
    MEDIUM   = (2, "Średni",   "#F59E0B")
    HIGH     = (3, "Wysoki",   "#EF4444")
    CRITICAL = (4, "Krytyczny","#7C3AED")

    def __init__(self, level: int, label: str, color: str):
        self._value_ = level
        self.label = label
        self.color = color

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """Wyznacza poziom ryzyka na podstawie wyniku (0.0–1.0)."""
        if score >= 0.85:  return cls.CRITICAL
        if score >= 0.65:  return cls.HIGH
        if score >= 0.40:  return cls.MEDIUM
        if score >= 0.15:  return cls.LOW
        return cls.NONE


class AlertSeverity(Enum):
    """Poziomy ważności alertów."""
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


class SystemState(Enum):
    """Stany systemu DARTRIX FLINT EDGE."""
    INITIALIZING = "initializing"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    MAINTENANCE  = "maintenance"
    EMERGENCY    = "emergency"
    SHUTDOWN     = "shutdown"


@dataclass
class Alert:
    """Alert systemowy."""

    alert_id:   str           = field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity:   AlertSeverity = AlertSeverity.INFO
    title:      str           = ""
    message:    str           = ""
    source:     str           = "system"
    timestamp:  datetime      = field(default_factory=datetime.now)
    resolved:   bool          = False
    metadata:   Dict[str, Any] = field(default_factory=dict)
    tags:       List[str]     = field(default_factory=list)

    def resolve(self, note: str = ""):
        self.resolved = True
        self.metadata["resolved_at"] = datetime.now().isoformat()
        self.metadata["resolution_note"] = note

    def to_dict(self) -> Dict:
        return {
            "alert_id":  self.alert_id,
            "severity":  self.severity.value,
            "title":     self.title,
            "message":   self.message,
            "source":    self.source,
            "timestamp": self.timestamp.isoformat(),
            "resolved":  self.resolved,
            "metadata":  self.metadata,
            "tags":      self.tags,
        }

    def __repr__(self):
        return f"<Alert [{self.severity.value.upper()}] {self.title}>"


@dataclass
class SystemStatus:
    """Aktualny status systemu."""

    state:          SystemState    = SystemState.RUNNING
    risk_level:     RiskLevel      = RiskLevel.NONE
    active_alerts:  int            = 0
    processed_signals: int         = 0
    decisions_made: int            = 0
    uptime_seconds: float          = 0.0
    last_updated:   datetime       = field(default_factory=datetime.now)
    modules:        Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "state":              self.state.value,
            "risk_level":         self.risk_level.label,
            "risk_color":         self.risk_level.color,
            "active_alerts":      self.active_alerts,
            "processed_signals":  self.processed_signals,
            "decisions_made":     self.decisions_made,
            "uptime_seconds":     round(self.uptime_seconds, 1),
            "last_updated":       self.last_updated.isoformat(),
            "modules":            self.modules,
        }