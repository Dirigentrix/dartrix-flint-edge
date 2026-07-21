"""
src/services/wolfguardian/wolf_security.py
-------------------------------------------
WolfGuardian Security Monitor — detekcja zagrożeń i ataków.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import hashlib
import secrets
from typing import List, Dict, Optional, Set
from collections import defaultdict, deque
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.models import Alert, AlertSeverity, RiskLevel


class ThreatType:
    REPLAY_ATTACK    = "replay_attack"
    BRUTE_FORCE      = "brute_force"
    SIGNAL_SPOOFING  = "signal_spoofing"
    DATA_TAMPERING   = "data_tampering"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALOUS_PATTERN   = "anomalous_pattern"
    SIGNAL_JAMMING   = "signal_jamming"


class ThreatEvent:
    """Zdarzenie zagrożenia bezpieczeństwa."""

    def __init__(self, threat_type: str, source: str,
                 severity: AlertSeverity, description: str,
                 evidence: Dict = None):
        self.event_id    = secrets.token_hex(6)
        self.threat_type = threat_type
        self.source      = source
        self.severity    = severity
        self.description = description
        self.evidence    = evidence or {}
        self.timestamp   = datetime.datetime.now()
        self.mitigated   = False
        self.mitigation  = ""

    def mitigate(self, action: str):
        self.mitigated = True
        self.mitigation = action

    def to_dict(self) -> Dict:
        return {
            "event_id":    self.event_id,
            "threat_type": self.threat_type,
            "source":      self.source,
            "severity":    self.severity.value,
            "description": self.description,
            "evidence":    self.evidence,
            "timestamp":   self.timestamp.isoformat(),
            "mitigated":   self.mitigated,
            "mitigation":  self.mitigation,
        }


class SecurityMonitor:
    """
    Monitor bezpieczeństwa — wykrywa zagrożenia, śledzi ataki,
    zarządza listą zablokowanych źródeł.
    """

    def __init__(self, max_failed_attempts: int = 5,
                 block_duration_minutes: int = 30):
        self.max_failed_attempts = max_failed_attempts
        self.block_duration = datetime.timedelta(minutes=block_duration_minutes)

        # Śledzenie prób
        self._failed_attempts: Dict[str, int] = defaultdict(int)
        self._blocked_sources: Dict[str, datetime.datetime] = {}

        # Historia sygnałów (dla detekcji replay)
        self._signal_hashes: deque = deque(maxlen=50000)
        self._signal_timestamps: Dict[str, datetime.datetime] = {}

        # Zdarzenia
        self.threat_events: List[ThreatEvent] = []
        self.alerts: List[Alert] = []

        # Statystyki
        self.threats_detected: int = 0
        self.sources_blocked: int = 0
        self.signals_verified: int = 0

    # ── PUBLIC API ────────────────────────────────────────────

    def verify_signal(self, signal_id: str, source_id: str,
                      payload: Dict, timestamp: datetime.datetime) -> Dict:
        """
        Weryfikuje sygnał pod kątem bezpieczeństwa.
        Sprawdza: replay, tampering, blocked source.
        """
        self.signals_verified += 1
        threats = []

        # 1. Sprawdź czy źródło jest zablokowane
        if self.is_blocked(source_id):
            threat = self._create_threat(
                ThreatType.UNAUTHORIZED_ACCESS, source_id,
                AlertSeverity.CRITICAL,
                f"Signal from blocked source: {source_id}",
                {"signal_id": signal_id}
            )
            threats.append(threat)
            return self._verify_result(False, threats, "source_blocked")

        # 2. Sprawdź replay (hash payloadu)
        payload_hash = self._hash_payload(payload)
        if payload_hash in self._signal_hashes:
            self.record_failed_attempt(source_id)
            threat = self._create_threat(
                ThreatType.REPLAY_ATTACK, source_id,
                AlertSeverity.CRITICAL,
                f"Replay attack detected from {source_id}",
                {"signal_id": signal_id, "hash": payload_hash[:16]}
            )
            threats.append(threat)

        # 3. Sprawdź stary timestamp (>60s)
        age = (datetime.datetime.now() - timestamp).total_seconds()
        if age > 60:
            threat = self._create_threat(
                ThreatType.REPLAY_ATTACK, source_id,
                AlertSeverity.ERROR,
                f"Old timestamp: signal is {age:.0f}s old",
                {"signal_id": signal_id, "age_seconds": age}
            )
            threats.append(threat)

        # 4. Zarejestruj hash
        self._signal_hashes.append(payload_hash)
        self._signal_timestamps[signal_id] = datetime.datetime.now()

        is_safe = len(threats) == 0
        return self._verify_result(is_safe, threats,
                                   "ok" if is_safe else "threats_detected")

    def record_failed_attempt(self, source_id: str):
        """Rejestruje nieudaną próbę — może prowadzić do blokady."""
        self._failed_attempts[source_id] += 1
        if self._failed_attempts[source_id] >= self.max_failed_attempts:
            self.block_source(source_id, "too_many_failed_attempts")

    def block_source(self, source_id: str, reason: str = "manual"):
        """Blokuje źródło sygnałów."""
        self._blocked_sources[source_id] = datetime.datetime.now()
        self.sources_blocked += 1
        threat = self._create_threat(
            ThreatType.UNAUTHORIZED_ACCESS, source_id,
            AlertSeverity.CRITICAL,
            f"Source {source_id} blocked: {reason}",
            {"reason": reason, "attempts": self._failed_attempts.get(source_id, 0)}
        )
        self.threat_events.append(threat)

    def unblock_source(self, source_id: str):
        """Odblokowuje źródło."""
        self._blocked_sources.pop(source_id, None)
        self._failed_attempts[source_id] = 0

    def is_blocked(self, source_id: str) -> bool:
        """Sprawdza czy źródło jest zablokowane."""
        if source_id not in self._blocked_sources:
            return False
        blocked_at = self._blocked_sources[source_id]
        if datetime.datetime.now() - blocked_at > self.block_duration:
            self.unblock_source(source_id)
            return False
        return True

    def detect_jamming(self, rssi_values: List[float],
                       source_id: str = "unknown") -> Optional[ThreatEvent]:
        """Wykrywa zakłócenia sygnału (jamming) na podstawie RSSI."""
        if len(rssi_values) < 5:
            return None
        avg_rssi = sum(rssi_values) / len(rssi_values)
        if avg_rssi < -95:
            return self._create_threat(
                ThreatType.SIGNAL_JAMMING, source_id,
                AlertSeverity.ERROR,
                f"Possible signal jamming: avg RSSI={avg_rssi:.1f} dBm",
                {"avg_rssi": avg_rssi, "samples": len(rssi_values)}
            )
        return None

    def security_report(self) -> Dict:
        """Raport bezpieczeństwa."""
        by_type: Dict[str, int] = defaultdict(int)
        for e in self.threat_events:
            by_type[e.threat_type] += 1

        return {
            "threats_detected":  self.threats_detected,
            "sources_blocked":   self.sources_blocked,
            "signals_verified":  self.signals_verified,
            "blocked_sources":   list(self._blocked_sources.keys()),
            "threats_by_type":   dict(by_type),
            "unmitigated_threats": sum(1 for e in self.threat_events if not e.mitigated),
            "active_alerts":     len([a for a in self.alerts if not a.resolved]),
        }

    # ── PRIVATE ───────────────────────────────────────────────

    def _hash_payload(self, payload: Dict) -> str:
        """Oblicza hash payloadu dla detekcji replay."""
        import json
        content = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def _create_threat(self, threat_type: str, source: str,
                       severity: AlertSeverity, description: str,
                       evidence: Dict = None) -> ThreatEvent:
        self.threats_detected += 1
        event = ThreatEvent(threat_type, source, severity, description, evidence)
        self.threat_events.append(event)
        alert = Alert(
            severity = severity,
            title    = f"Security: {threat_type.replace('_', ' ').title()}",
            message  = description,
            source   = "wolf_security",
            tags     = ["security", threat_type],
        )
        self.alerts.append(alert)
        return event

    def _verify_result(self, is_safe: bool, threats: List[ThreatEvent],
                       status: str) -> Dict:
        return {
            "is_safe":       is_safe,
            "status":        status,
            "threats_count": len(threats),
            "threats":       [t.to_dict() for t in threats],
            "ts":            datetime.datetime.now().isoformat(),
        }