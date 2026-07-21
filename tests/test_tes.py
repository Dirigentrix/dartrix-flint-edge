"""
tests/test_tes.py
------------------
Testy jednostkowe modułu TES.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from domain.signal import Signal, SignalType
from domain.decision import DecisionStatus
from services.tes.tes_engine import TESEngine
from services.tes.tes_rules import RuleSet, Rule, RuleAction, RulePriority


def test_tes_no_triggers():
    """Test: brak wyzwolonych reguł — niska decyzja."""
    tes = TESEngine(auto_execute=True)
    ctx = {"temperature": 5.0, "temp_min": 2.0, "temp_max": 8.0,
           "humidity": 60.0, "battery_pct": 80.0, "risk_score": 0.1}
    decision = tes.evaluate(ctx)
    assert decision.score < 0.5
    assert decision.status == DecisionStatus.EXECUTED
    print("  ✅ test_tes_no_triggers")


def test_tes_temperature_breach():
    """Test: przekroczenie temperatury wyzwala reguły."""
    tes = TESEngine(auto_execute=True)
    ctx = {"temperature": 15.0, "temp_min": 2.0, "temp_max": 8.0,
           "risk_score": 0.6}
    decision = tes.evaluate(ctx)
    assert len(decision.source_rules) > 0
    assert "TEMP-001" in decision.source_rules
    print("  ✅ test_tes_temperature_breach")


def test_tes_critical_risk():
    """Test: krytyczny risk score wyzwala eskalację."""
    tes = TESEngine(auto_execute=True)
    ctx = {"risk_score": 0.95, "temperature": 25.0,
           "temp_min": 2.0, "temp_max": 8.0}
    decision = tes.evaluate(ctx)
    assert decision.score >= 0.7
    assert "RISK-002" in decision.source_rules
    print("  ✅ test_tes_critical_risk")


def test_tes_replay_attack():
    """Test: replay attack wyzwala eskalację."""
    tes = TESEngine(auto_execute=True)
    ctx = {"replay_detected": True, "risk_score": 0.95}
    decision = tes.evaluate(ctx)
    assert "SEC-001" in decision.source_rules
    print("  ✅ test_tes_replay_attack")


def test_tes_low_battery():
    """Test: niska bateria wyzwala powiadomienie."""
    tes = TESEngine(auto_execute=True)
    ctx = {"battery_pct": 8.0, "risk_score": 0.1}
    decision = tes.evaluate(ctx)
    assert "BAT-001" in decision.source_rules
    print("  ✅ test_tes_low_battery")


def test_tes_audit_trail():
    """Test: ścieżka audytu jest wypełniona."""
    tes = TESEngine(auto_execute=True)
    ctx = {"temperature": 5.0, "temp_min": 2.0, "temp_max": 8.0}
    decision = tes.evaluate(ctx)
    assert len(decision.audit_trail) >= 1
    assert any(e["step"] == "rules_evaluated" for e in decision.audit_trail)
    print("  ✅ test_tes_audit_trail")


def test_tes_pending_mode():
    """Test: tryb pending (bez auto-execute)."""
    tes = TESEngine(auto_execute=False)
    ctx = {"temperature": 5.0, "temp_min": 2.0, "temp_max": 8.0}
    decision = tes.evaluate(ctx)
    assert decision.status == DecisionStatus.PENDING
    print("  ✅ test_tes_pending_mode")


def test_ruleset_custom_rule():
    """Test: dodawanie własnej reguły."""
    rs = RuleSet()
    custom = Rule(
        rule_id     = "CUSTOM-001",
        name        = "Custom Test Rule",
        description = "Testowa reguła",
        condition   = lambda ctx: ctx.get("custom_flag", False),
        action      = RuleAction.LOG,
        priority    = RulePriority.LOW,
    )
    rs.add(custom)
    triggered = rs.evaluate_all({"custom_flag": True})
    assert any(r["rule_id"] == "CUSTOM-001" for r in triggered)
    print("  ✅ test_ruleset_custom_rule")


def test_ruleset_disable_rule():
    """Test: wyłączanie reguły."""
    rs = RuleSet()
    rs.disable("TEMP-001")
    triggered = rs.evaluate_all({"temperature": 20.0, "temp_max": 8.0})
    assert not any(r["rule_id"] == "TEMP-001" for r in triggered)
    print("  ✅ test_ruleset_disable_rule")


def test_tes_stats():
    """Test: statystyki TES."""
    tes = TESEngine(auto_execute=True)
    for _ in range(5):
        tes.evaluate({"temperature": 5.0, "temp_min": 2.0, "temp_max": 8.0})
    stats = tes.stats()
    assert stats["decisions_count"] == 5
    print("  ✅ test_tes_stats")


def run_all():
    print("\n  === TES Tests ===")
    test_tes_no_triggers()
    test_tes_temperature_breach()
    test_tes_critical_risk()
    test_tes_replay_attack()
    test_tes_low_battery()
    test_tes_audit_trail()
    test_tes_pending_mode()
    test_ruleset_custom_rule()
    test_ruleset_disable_rule()
    test_tes_stats()
    print("  All TES tests passed! ✅\n")


if __name__ == "__main__":
    run_all()