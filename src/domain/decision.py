"""
src/domain/decision.py
----------------------
Model decyzji — reprezentuje wynik procesu decyzyjnego.
DARTRIX FLINT EDGE v0.9 RC
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class DecisionType(Enum):
    """Typy decyzji systemowych."""
    RISK_ASSESSMENT  = "risk_assessment"
    INTERVENTION     = "intervention"
    ALERT            = "alert"
    CONFIG_CHANGE    = "config_change"
    SYSTEM_SHUTDOWN  = "system_shutdown"
    MAINTENANCE      = "maintenance"
    ESCALATION       = "escalation"


class DecisionStatus(Enum):
    """Status decyzji."""
    PENDING    = "pending"
    APPROVED   = "approved"
    REJECTED   = "rejected"
    EXECUTED   = "executed"
    FAILED     = "failed"
    OVERRIDDEN = "overridden"


@dataclass
class Decision:
    """Reprezentacja podjętej decyzji systemowej."""

    decision_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type:  DecisionType   = DecisionType.RISK_ASSESSMENT
    status:         DecisionStatus = DecisionStatus.PENDING
    timestamp:      datetime       = field(default_factory=datetime.now)

    # Źródło
    source_module:  str            = ""
    source_rules:   List[str]      = field(default_factory=list)

    # Dane wejściowe
    input_signals:  List[Dict]     = field(default_factory=list)
    input_context:  Dict[str, Any] = field(default_factory=dict)

    # Wynik
    score:          float          = 0.0
    confidence:     float          = 0.0
    recommendation: str            = ""
    alternatives:   List[Dict]     = field(default_factory=list)

    # Audyt
    audit_trail:    List[Dict]     = field(default_factory=list)
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def add_audit_entry(self, step: str, data: Dict = None):
        """Dodaje wpis do ścieżki audytu."""
        self.audit_trail.append({
            "step":      step,
            "data":      data or {},
            "timestamp": datetime.now().isoformat(),
        })

    def approve(self, approver: str = "system"):
        self.status = DecisionStatus.APPROVED
        self.add_audit_entry("approved", {"approver": approver})

    def execute(self, result: str = ""):
        self.status = DecisionStatus.EXECUTED
        self.add_audit_entry("executed", {"result": result})

    def reject(self, reason: str = ""):
        self.status = DecisionStatus.REJECTED
        self.add_audit_entry("rejected", {"reason": reason})

    def to_dict(self) -> Dict:
        return {
            "decision_id":    self.decision_id,
            "decision_type":  self.decision_type.value,
            "status":         self.status.value,
            "timestamp":      self.timestamp.isoformat(),
            "source_module":  self.source_module,
            "source_rules":   self.source_rules,
            "input_signals":  self.input_signals,
            "input_context":  self.input_context,
            "score":          self.score,
            "confidence":     self.confidence,
            "recommendation": self.recommendation,
            "alternatives":   self.alternatives,
            "audit_trail":    self.audit_trail,
            "metadata":       self.metadata,
        }

    def __repr__(self):
        return (f"<Decision [{self.decision_type.value}] "
                f"score={self.score:.2f} "
                f"status={self.status.value}>")