"""
src/services/wolfguardian/wolf_core.py
---------------------------------------
WolfGuardian Core — główny moduł bezpieczeństwa i nadzoru.
Integruje SecurityMonitor i AlertManager.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
from typing import List, Dict, Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal
from domain.models import Alert, AlertSeverity, RiskLevel, SystemState
from services.wolfguardian.wolf_security import SecurityMonitor
from services.wolfguardian.wolf_alerts import AlertManager


class WolfGuardian:
    """
    WolfGuardian — strażnik systemu DARTRIX FLINT EDGE.
    Integruje bezpieczeństwo, alerty i nadzór systemowy.

    Motto: "Wilk nie śpi. Wilk czuwa."
    """

    VERSION = "0.9-RC"

    def __init__(self, auto_block: bool = True,
                 max_failed_attempts: int = 5):
        self.security   = SecurityMonitor(max_failed_attempts=max_failed_attempts)
        self.alert_mgr  = AlertManager()
        self.auto_block = auto_block

        self.system_state = SystemState.RUNNING
        self.watch_log: List[Dict] = []
        self.started_at = datetime.datetime.now()
        self.signals_watched: int = 0

    # ── PUBLIC API ────────────────────────────────────────────

    def watch(self, signal: Signal) -> Dict:
        """
        Nadzoruje sygnał — weryfikuje bezpieczeństwo i routuje alerty.

        Returns:
            dict z wynikiem nadzoru
        """
        self.signals_watched += 1

        # 1. Weryfikacja bezpieczeństwa
        # Używamy stabilnego payloadu (bez signal_id/timestamp) dla detekcji replay
        stable_payload = {
            "value":       signal.value,
            "signal_type": signal.signal_type.value,
            "source_id":   signal.source_id,
            "unit":        signal.unit,
        }
        verify_result = self.security.verify_signal(
            signal_id  = signal.signal_id,
            source_id  = signal.source_id,
            payload    = stable_payload,
            timestamp  = signal.timestamp,
        )

        # 2. Przetwarzanie zagrożeń
        threats = verify_result.get("threats", [])
        for threat in threats:
            alert = Alert(
                severity = AlertSeverity(threat.get("severity", "warning")),
                title    = f"WolfGuardian: {threat.get('threat_type', 'unknown')}",
                message  = threat.get("description", ""),
                source   = "wolf_guardian",
                tags     = ["security", threat.get("threat_type", "")],
            )
            self.alert_mgr.receive(alert)

        # 3. Auto-blokada
        if self.auto_block and not verify_result["is_safe"]:
            if verify_result.get("status") == "threats_detected":
                self.security.record_failed_attempt(signal.source_id)

        # 4. Log
        entry = {
            "signal_id":  signal.signal_id,
            "source_id":  signal.source_id,
            "is_safe":    verify_result["is_safe"],
            "threats":    len(threats),
            "ts":         datetime.datetime.now().isoformat(),
        }
        self.watch_log.append(entry)
        if len(self.watch_log) > 1000:
            self.watch_log.pop(0)

        return {
            "watched":       True,
            "signal_id":     signal.signal_id,
            "is_safe":       verify_result["is_safe"],
            "threats_count": len(threats),
            "verify_status": verify_result["status"],
            "system_state":  self.system_state.value,
        }

    def receive_alert(self, alert: Alert) -> Dict:
        """Przyjmuje alert z zewnętrznego modułu."""
        result = self.alert_mgr.receive(alert)

        # Aktualizacja stanu systemu
        if alert.severity == AlertSeverity.CRITICAL:
            if self.system_state == SystemState.RUNNING:
                self.system_state = SystemState.DEGRADED

        return result

    def receive_alerts_batch(self, alerts: List[Alert]) -> List[Dict]:
        return [self.receive_alert(a) for a in alerts]

    def block_source(self, source_id: str, reason: str = "manual"):
        """Ręczna blokada źródła."""
        self.security.block_source(source_id, reason)

    def unblock_source(self, source_id: str):
        """Odblokowanie źródła."""
        self.security.unblock_source(source_id)

    def resolve_alert(self, alert_id: str, note: str = "") -> bool:
        """Rozwiązuje alert."""
        return self.alert_mgr.resolve(alert_id, note)

    def set_system_state(self, state: SystemState):
        """Ustawia stan systemu."""
        old = self.system_state
        self.system_state = state
        self.watch_log.append({
            "event":    "state_change",
            "from":     old.value,
            "to":       state.value,
            "ts":       datetime.datetime.now().isoformat(),
        })

    def full_report(self) -> Dict:
        """Pełny raport WolfGuardian."""
        uptime = (datetime.datetime.now() - self.started_at).total_seconds()
        return {
            "module":          "WolfGuardian",
            "version":         self.VERSION,
            "system_state":    self.system_state.value,
            "signals_watched": self.signals_watched,
            "uptime_seconds":  round(uptime, 1),
            "security":        self.security.security_report(),
            "alerts":          self.alert_mgr.summary(),
            "watch_log_size":  len(self.watch_log),
        }

    def stats(self) -> Dict:
        return self.full_report()