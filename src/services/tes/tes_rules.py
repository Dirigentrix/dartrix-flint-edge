"""
src/services/tes/tes_rules.py
------------------------------
TES Rules — system reguł decyzyjnych.
TES = Telemetry Engine System
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
from enum import Enum


class RuleAction(Enum):
    """Akcje wynikające z reguły."""
    ALERT          = "alert"
    ESCALATE       = "escalate"
    SHUTDOWN       = "shutdown"
    MAINTENANCE    = "maintenance"
    LOG            = "log"
    NOTIFY         = "notify"
    THROTTLE       = "throttle"
    RECALIBRATE    = "recalibrate"


class RulePriority(Enum):
    """Priorytety reguł."""
    LOW      = 1
    NORMAL   = 2
    HIGH     = 3
    CRITICAL = 4


@dataclass
class Rule:
    """Pojedyncza reguła decyzyjna."""

    rule_id:     str
    name:        str
    description: str
    condition:   Callable[[Dict], bool]
    action:      RuleAction
    priority:    RulePriority = RulePriority.NORMAL
    enabled:     bool         = True
    tags:        List[str]    = field(default_factory=list)
    metadata:    Dict         = field(default_factory=dict)

    # Statystyki
    triggered_count: int = field(default=0, init=False)
    last_triggered:  Optional[datetime.datetime] = field(default=None, init=False)

    def evaluate(self, context: Dict) -> bool:
        """Ewaluuje regułę dla danego kontekstu."""
        if not self.enabled:
            return False
        try:
            result = self.condition(context)
            if result:
                self.triggered_count += 1
                self.last_triggered = datetime.datetime.now()
            return result
        except Exception:
            return False

    def to_dict(self) -> Dict:
        return {
            "rule_id":         self.rule_id,
            "name":            self.name,
            "description":     self.description,
            "action":          self.action.value,
            "priority":        self.priority.value,
            "enabled":         self.enabled,
            "tags":            self.tags,
            "triggered_count": self.triggered_count,
            "last_triggered":  self.last_triggered.isoformat() if self.last_triggered else None,
        }


class RuleSet:
    """Zestaw reguł decyzyjnych — Cold Chain + Security."""

    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self._build_default_rules()

    def _build_default_rules(self):
        """Buduje domyślny zestaw reguł."""

        # ── TEMPERATURA ───────────────────────────────────────
        self.add(Rule(
            rule_id     = "TEMP-001",
            name        = "Temperature Above Max",
            description = "Temperatura przekracza maksimum profilu",
            condition   = lambda ctx: ctx.get("temperature", 0) > ctx.get("temp_max", 8.0),
            action      = RuleAction.ALERT,
            priority    = RulePriority.HIGH,
            tags        = ["temperature", "cold_chain"],
        ))

        self.add(Rule(
            rule_id     = "TEMP-002",
            name        = "Temperature Below Min",
            description = "Temperatura poniżej minimum profilu",
            condition   = lambda ctx: ctx.get("temperature", 0) < ctx.get("temp_min", -25.0),
            action      = RuleAction.ALERT,
            priority    = RulePriority.HIGH,
            tags        = ["temperature", "cold_chain"],
        ))

        self.add(Rule(
            rule_id     = "TEMP-003",
            name        = "Critical Temperature Excursion",
            description = "Krytyczne przekroczenie temperatury (>5°C od progu)",
            condition   = lambda ctx: (
                ctx.get("temperature", 0) > ctx.get("temp_max", 8.0) + 5.0 or
                ctx.get("temperature", 0) < ctx.get("temp_min", -25.0) - 5.0
            ),
            action      = RuleAction.ESCALATE,
            priority    = RulePriority.CRITICAL,
            tags        = ["temperature", "critical", "cold_chain"],
        ))

        # ── WILGOTNOŚĆ ────────────────────────────────────────
        self.add(Rule(
            rule_id     = "HUM-001",
            name        = "High Humidity",
            description = "Wilgotność powyżej 90%",
            condition   = lambda ctx: ctx.get("humidity", 0) > 90.0,
            action      = RuleAction.ALERT,
            priority    = RulePriority.NORMAL,
            tags        = ["humidity"],
        ))

        # ── BATERIA ───────────────────────────────────────────
        self.add(Rule(
            rule_id     = "BAT-001",
            name        = "Low Battery",
            description = "Poziom baterii poniżej 15%",
            condition   = lambda ctx: ctx.get("battery_pct", 100) < 15.0,
            action      = RuleAction.NOTIFY,
            priority    = RulePriority.NORMAL,
            tags        = ["battery", "maintenance"],
        ))

        self.add(Rule(
            rule_id     = "BAT-002",
            name        = "Critical Battery",
            description = "Poziom baterii poniżej 5%",
            condition   = lambda ctx: ctx.get("battery_pct", 100) < 5.0,
            action      = RuleAction.MAINTENANCE,
            priority    = RulePriority.HIGH,
            tags        = ["battery", "critical"],
        ))

        # ── BEZPIECZEŃSTWO ────────────────────────────────────
        self.add(Rule(
            rule_id     = "SEC-001",
            name        = "Replay Attack",
            description = "Wykryto atak replay na sygnał",
            condition   = lambda ctx: ctx.get("replay_detected", False),
            action      = RuleAction.ESCALATE,
            priority    = RulePriority.CRITICAL,
            tags        = ["security", "replay"],
        ))

        self.add(Rule(
            rule_id     = "SEC-002",
            name        = "Signal Loss",
            description = "Utrata sygnału przez ponad 5 minut",
            condition   = lambda ctx: ctx.get("signal_loss", False),
            action      = RuleAction.ALERT,
            priority    = RulePriority.HIGH,
            tags        = ["signal", "connectivity"],
        ))

        # ── RYZYKO ────────────────────────────────────────────
        self.add(Rule(
            rule_id     = "RISK-001",
            name        = "High Risk Score",
            description = "Wynik ryzyka powyżej 0.7",
            condition   = lambda ctx: ctx.get("risk_score", 0) > 0.7,
            action      = RuleAction.ESCALATE,
            priority    = RulePriority.HIGH,
            tags        = ["risk"],
        ))

        self.add(Rule(
            rule_id     = "RISK-002",
            name        = "Critical Risk Score",
            description = "Wynik ryzyka powyżej 0.9",
            condition   = lambda ctx: ctx.get("risk_score", 0) > 0.9,
            action      = RuleAction.SHUTDOWN,
            priority    = RulePriority.CRITICAL,
            tags        = ["risk", "critical"],
        ))

        # ── DRZWI ─────────────────────────────────────────────
        self.add(Rule(
            rule_id     = "DOOR-001",
            name        = "Door Open Alert",
            description = "Drzwi chłodni otwarte",
            condition   = lambda ctx: ctx.get("door_open", False),
            action      = RuleAction.ALERT,
            priority    = RulePriority.NORMAL,
            tags        = ["door", "cold_chain"],
        ))

    def add(self, rule: Rule):
        self.rules[rule.rule_id] = rule

    def remove(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def enable(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def evaluate_all(self, context: Dict) -> List[Dict]:
        """Ewaluuje wszystkie reguły dla kontekstu. Zwraca wyzwolone reguły."""
        triggered = []
        for rule in sorted(self.rules.values(),
                           key=lambda r: r.priority.value, reverse=True):
            if rule.evaluate(context):
                triggered.append({
                    "rule_id":    rule.rule_id,
                    "name":       rule.name,
                    "action":     rule.action.value,
                    "priority":   rule.priority.value,
                    "tags":       rule.tags,
                })
        return triggered

    def list_rules(self) -> List[Dict]:
        return [r.to_dict() for r in self.rules.values()]

    def stats(self) -> Dict:
        enabled = [r for r in self.rules.values() if r.enabled]
        return {
            "total_rules":   len(self.rules),
            "enabled_rules": len(enabled),
            "total_triggers": sum(r.triggered_count for r in self.rules.values()),
            "by_priority": {
                p.name: sum(1 for r in self.rules.values() if r.priority == p)
                for p in RulePriority
            },
        }