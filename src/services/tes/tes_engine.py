"""
src/services/tes/tes_engine.py
-------------------------------
TES Engine — silnik decyzyjny systemu DARTRIX FLINT EDGE.
TES = Telemetry Engine System
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
from typing import List, Dict, Optional, Any
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal
from domain.decision import Decision, DecisionType, DecisionStatus
from domain.models import RiskLevel, Alert, AlertSeverity
from services.tes.tes_rules import RuleSet, RuleAction


class TESEngine:
    """
    Silnik decyzyjny TES — przetwarza kontekst telemetryczny,
    ewaluuje reguły i generuje decyzje systemowe.
    """

    VERSION = "0.9-RC"

    def __init__(self, auto_execute: bool = True):
        """
        Args:
            auto_execute: Czy automatycznie wykonywać decyzje (bez oczekiwania na zatwierdzenie)
        """
        self.rule_set = RuleSet()
        self.auto_execute = auto_execute
        self.decisions: List[Decision] = []
        self.alerts: List[Alert] = []
        self.decisions_count: int = 0
        self.started_at = datetime.datetime.now()

    # ── PUBLIC API ────────────────────────────────────────────

    def evaluate(self, context: Dict[str, Any],
                 source_module: str = "tes") -> Decision:
        """
        Ewaluuje kontekst telemetryczny i podejmuje decyzję.

        Args:
            context:       Słownik z danymi telemetrycznymi
            source_module: Nazwa modułu źródłowego

        Returns:
            Decision z wynikiem ewaluacji
        """
        self.decisions_count += 1

        # 1. Ewaluacja reguł
        triggered_rules = self.rule_set.evaluate_all(context)

        # 2. Obliczenie score decyzji
        score, confidence = self._calculate_score(triggered_rules, context)

        # 3. Wyznaczenie typu decyzji
        decision_type = self._determine_type(triggered_rules)

        # 4. Generowanie rekomendacji
        recommendation = self._generate_recommendation(triggered_rules, context)

        # 5. Tworzenie decyzji
        decision = Decision(
            decision_type  = decision_type,
            source_module  = source_module,
            source_rules   = [r["rule_id"] for r in triggered_rules],
            input_context  = context,
            score          = score,
            confidence     = confidence,
            recommendation = recommendation,
        )

        # 6. Ścieżka audytu
        decision.add_audit_entry("rules_evaluated", {
            "total_rules":    len(self.rule_set.rules),
            "triggered":      len(triggered_rules),
            "triggered_ids":  [r["rule_id"] for r in triggered_rules],
        })

        # 7. Generowanie alertów
        for rule in triggered_rules:
            if rule["action"] in ("alert", "escalate", "shutdown"):
                alert = self._create_alert(rule, context, score)
                self.alerts.append(alert)
                decision.add_audit_entry("alert_created", {"alert_id": alert.alert_id})

        # 8. Wykonanie decyzji
        if self.auto_execute:
            decision.approve("auto")
            decision.execute(f"Auto-executed: {recommendation[:80]}")
        else:
            decision.status = DecisionStatus.PENDING

        self.decisions.append(decision)
        return decision

    def evaluate_signal(self, signal: Signal,
                        extra_context: Dict = None) -> Decision:
        """Ewaluuje pojedynczy sygnał."""
        context = {
            "signal_id":   signal.signal_id,
            "signal_type": signal.signal_type.value,
            "value":       signal.value,
            "source_id":   signal.source_id,
            "timestamp":   signal.timestamp.isoformat(),
            "confidence":  signal.confidence,
        }
        # Mapowanie wartości na klucze kontekstowe
        type_map = {
            "temperature": "temperature",
            "humidity":    "humidity",
            "pressure":    "pressure",
            "co2":         "co2",
            "vibration":   "vibration",
        }
        key = type_map.get(signal.signal_type.value)
        if key:
            context[key] = signal.value

        if extra_context:
            context.update(extra_context)

        return self.evaluate(context, source_module="tes_signal")

    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        """Zwraca ostatnie decyzje."""
        return [d.to_dict() for d in self.decisions[-limit:]]

    def get_active_alerts(self) -> List[Dict]:
        """Zwraca aktywne alerty."""
        return [a.to_dict() for a in self.alerts if not a.resolved]

    def stats(self) -> Dict:
        uptime = (datetime.datetime.now() - self.started_at).total_seconds()
        executed = [d for d in self.decisions if d.status == DecisionStatus.EXECUTED]
        return {
            "module":           "TES Engine",
            "version":          self.VERSION,
            "decisions_count":  self.decisions_count,
            "executed":         len(executed),
            "active_alerts":    len(self.get_active_alerts()),
            "total_alerts":     len(self.alerts),
            "uptime_seconds":   round(uptime, 1),
            "auto_execute":     self.auto_execute,
            "rules":            self.rule_set.stats(),
        }

    # ── PRIVATE ───────────────────────────────────────────────

    def _calculate_score(self, triggered: List[Dict],
                         context: Dict) -> tuple[float, float]:
        """Oblicza score i confidence decyzji."""
        if not triggered:
            return 0.0, 0.95

        # Waga priorytetów
        priority_weights = {4: 1.0, 3: 0.7, 2: 0.4, 1: 0.2}
        max_priority = max(r["priority"] for r in triggered)
        score = min(1.0, sum(
            priority_weights.get(r["priority"], 0.3)
            for r in triggered
        ) / max(1, len(triggered)))

        # Uwzględnij risk_score z kontekstu
        ctx_risk = context.get("risk_score", 0.0)
        score = max(score, ctx_risk)

        confidence = min(0.99, 0.6 + len(triggered) * 0.08)
        return round(score, 4), round(confidence, 4)

    def _determine_type(self, triggered: List[Dict]) -> DecisionType:
        """Wyznacza typ decyzji na podstawie wyzwolonych reguł."""
        actions = {r["action"] for r in triggered}
        if "shutdown" in actions:
            return DecisionType.SYSTEM_SHUTDOWN
        if "escalate" in actions:
            return DecisionType.ESCALATION
        if "maintenance" in actions:
            return DecisionType.MAINTENANCE
        if "alert" in actions or "notify" in actions:
            return DecisionType.ALERT
        return DecisionType.RISK_ASSESSMENT

    def _generate_recommendation(self, triggered: List[Dict],
                                  context: Dict) -> str:
        """Generuje rekomendację tekstową."""
        if not triggered:
            return "System w normie. Brak wymaganych działań."

        actions = [r["action"] for r in triggered]
        names = [r["name"] for r in triggered[:3]]

        if "shutdown" in actions:
            return f"KRYTYCZNE: Natychmiastowe wyłączenie systemu. Reguły: {', '.join(names)}"
        if "escalate" in actions:
            return f"ESKALACJA: Wymagana interwencja operatora. Reguły: {', '.join(names)}"
        if "maintenance" in actions:
            return f"KONSERWACJA: Zaplanuj serwis. Reguły: {', '.join(names)}"
        return f"ALERT: Monitoruj sytuację. Reguły: {', '.join(names)}"

    def _create_alert(self, rule: Dict, context: Dict,
                      score: float) -> Alert:
        """Tworzy alert na podstawie wyzwolonej reguły."""
        action = rule["action"]
        severity_map = {
            "shutdown":  AlertSeverity.CRITICAL,
            "escalate":  AlertSeverity.CRITICAL,
            "alert":     AlertSeverity.ERROR,
            "notify":    AlertSeverity.WARNING,
            "maintenance": AlertSeverity.WARNING,
        }
        return Alert(
            severity = severity_map.get(action, AlertSeverity.INFO),
            title    = f"TES: {rule['name']}",
            message  = f"Rule {rule['rule_id']} triggered. Score: {score:.3f}",
            source   = "tes_engine",
            metadata = {"rule": rule, "context_keys": list(context.keys())},
            tags     = rule.get("tags", []) + ["tes"],
        )