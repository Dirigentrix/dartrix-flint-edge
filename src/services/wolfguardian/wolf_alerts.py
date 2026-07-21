"""
src/services/wolfguardian/wolf_alerts.py
-----------------------------------------
WolfGuardian Alert Manager — zarządzanie alertami i powiadomieniami.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
from typing import List, Dict, Optional, Callable
from collections import defaultdict
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.models import Alert, AlertSeverity


class AlertChannel:
    """Kanał powiadomień."""

    def __init__(self, name: str, handler: Callable[[Alert], None],
                 min_severity: AlertSeverity = AlertSeverity.INFO):
        self.name = name
        self.handler = handler
        self.min_severity = min_severity
        self.sent_count: int = 0
        self.enabled: bool = True

    def should_send(self, alert: Alert) -> bool:
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING,
                          AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        return (self.enabled and
                severity_order.index(alert.severity) >=
                severity_order.index(self.min_severity))

    def send(self, alert: Alert) -> bool:
        if not self.should_send(alert):
            return False
        try:
            self.handler(alert)
            self.sent_count += 1
            return True
        except Exception:
            return False


class AlertManager:
    """
    Menedżer alertów — agreguje, deduplikuje, routuje i śledzi alerty.
    """

    def __init__(self, dedup_window_seconds: int = 300):
        self.alerts: List[Alert] = []
        self.channels: Dict[str, AlertChannel] = {}
        self.dedup_window = datetime.timedelta(seconds=dedup_window_seconds)
        self._recent_titles: Dict[str, datetime.datetime] = {}

        # Statystyki
        self.total_received: int = 0
        self.total_sent: int = 0
        self.total_deduplicated: int = 0
        self.total_resolved: int = 0

        # Domyślny kanał (log)
        self.add_channel("console", lambda a: print(
            f"[{a.severity.value.upper()}] {a.title}: {a.message}"
        ))

    def add_channel(self, name: str, handler: Callable,
                    min_severity: AlertSeverity = AlertSeverity.INFO) -> AlertChannel:
        channel = AlertChannel(name, handler, min_severity)
        self.channels[name] = channel
        return channel

    def receive(self, alert: Alert) -> Dict:
        """Przyjmuje alert, deduplikuje i routuje do kanałów."""
        self.total_received += 1

        # Deduplikacja
        if self._is_duplicate(alert):
            self.total_deduplicated += 1
            return {"status": "deduplicated", "alert_id": alert.alert_id}

        self.alerts.append(alert)
        self._recent_titles[alert.title] = datetime.datetime.now()

        # Routing do kanałów
        sent_to = []
        for name, channel in self.channels.items():
            if channel.send(alert):
                sent_to.append(name)
                self.total_sent += 1

        return {
            "status":   "sent",
            "alert_id": alert.alert_id,
            "sent_to":  sent_to,
        }

    def receive_batch(self, alerts: List[Alert]) -> List[Dict]:
        return [self.receive(a) for a in alerts]

    def resolve(self, alert_id: str, note: str = "") -> bool:
        for alert in self.alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolve(note)
                self.total_resolved += 1
                return True
        return False

    def resolve_by_tag(self, tag: str, note: str = "") -> int:
        """Rozwiązuje wszystkie alerty z danym tagiem."""
        count = 0
        for alert in self.alerts:
            if tag in alert.tags and not alert.resolved:
                alert.resolve(note)
                self.total_resolved += 1
                count += 1
        return count

    def get_active(self, severity: AlertSeverity = None) -> List[Alert]:
        active = [a for a in self.alerts if not a.resolved]
        if severity:
            active = [a for a in active if a.severity == severity]
        return active

    def get_by_source(self, source: str) -> List[Alert]:
        return [a for a in self.alerts if a.source == source]

    def summary(self) -> Dict:
        active = self.get_active()
        by_severity: Dict[str, int] = defaultdict(int)
        for a in active:
            by_severity[a.severity.value] += 1

        return {
            "total_received":     self.total_received,
            "total_sent":         self.total_sent,
            "total_deduplicated": self.total_deduplicated,
            "total_resolved":     self.total_resolved,
            "active_alerts":      len(active),
            "by_severity":        dict(by_severity),
            "channels":           {
                name: {"sent": ch.sent_count, "enabled": ch.enabled}
                for name, ch in self.channels.items()
            },
        }

    def _is_duplicate(self, alert: Alert) -> bool:
        last_seen = self._recent_titles.get(alert.title)
        if last_seen is None:
            return False
        return datetime.datetime.now() - last_seen < self.dedup_window