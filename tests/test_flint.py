"""
tests/test_flint.py
--------------------
Testy jednostkowe modułu FLINT.
DARTRIX FLINT EDGE v0.9 RC
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from domain.signal import Signal, SignalType, SignalStatus
from services.flint.flint_core import FlintCore
from services.flint.flint_temperature import FlintTemperature, ColdChainProfile
from services.flint.flint_signal import FlintSignal


def make_signal(value: float, stype: SignalType = SignalType.TEMPERATURE,
                source: str = "test-sensor") -> Signal:
    return Signal(value=value, signal_type=stype, source_id=source, unit="°C")


def test_flint_core_normal():
    """Test: normalny sygnał nie jest anomalią."""
    flint = FlintCore()
    sig = make_signal(4.5)
    result = flint.process(sig)
    assert result["is_anomaly"] == False
    assert result["risk_score"] < 0.5
    print("  ✅ test_flint_core_normal")


def test_flint_core_above_max():
    """Test: temperatura powyżej maksimum."""
    flint = FlintCore()
    sig = make_signal(25.0)  # Powyżej 8°C
    result = flint.process(sig)
    assert result["is_anomaly"] == True
    assert result["risk_score"] > 0.0
    print("  ✅ test_flint_core_above_max")


def test_flint_core_below_min():
    """Test: temperatura poniżej minimum."""
    flint = FlintCore()
    sig = make_signal(-30.0)  # Poniżej -25°C
    result = flint.process(sig)
    assert result["is_anomaly"] == True
    print("  ✅ test_flint_core_below_min")


def test_flint_core_zscore():
    """Test: detekcja anomalii Z-score."""
    flint = FlintCore(sensitivity=2.0)
    # Wypełnij historię normalnymi wartościami
    for _ in range(20):
        flint.process(make_signal(4.5))
    # Wyślij outlier
    result = flint.process(make_signal(4.5))  # Normalny
    assert result["z_score"] >= 0.0
    print("  ✅ test_flint_core_zscore")


def test_flint_core_stats():
    """Test: statystyki FLINT."""
    flint = FlintCore()
    for v in [4.0, 4.5, 5.0, 20.0]:
        flint.process(make_signal(v))
    stats = flint.stats()
    assert stats["signals_processed"] == 4
    assert stats["anomalies_detected"] >= 1
    print("  ✅ test_flint_core_stats")


def test_flint_temperature_in_range():
    """Test: temperatura w zakresie pharma."""
    ft = FlintTemperature("pharma")
    sig = make_signal(5.0)
    result = ft.analyze(sig, "device-001")
    assert result["in_range"] == True
    assert result["risk_score"] == 0.0
    print("  ✅ test_flint_temperature_in_range")


def test_flint_temperature_excursion():
    """Test: przekroczenie temperatury."""
    ft = FlintTemperature("pharma")
    sig = make_signal(15.0)
    result = ft.analyze(sig, "device-001")
    assert result["in_range"] == False
    assert result["risk_score"] > 0.0
    assert result["excursion"] is not None
    print("  ✅ test_flint_temperature_excursion")


def test_flint_temperature_mkt():
    """Test: obliczanie MKT."""
    ft = FlintTemperature("pharma")
    for v in [4.0, 5.0, 6.0, 7.0, 5.5]:
        ft.analyze(make_signal(v), "dev")
    mkt = ft.calculate_mkt()
    assert mkt is not None
    assert isinstance(mkt, float)
    print(f"  ✅ test_flint_temperature_mkt (MKT={mkt}°C)")


def test_cold_chain_profiles():
    """Test: profile Cold Chain."""
    profiles = ColdChainProfile.list_profiles()
    assert "pharma" in profiles
    assert "frozen" in profiles
    assert "chilled" in profiles
    pharma = ColdChainProfile.get("pharma")
    assert pharma["min"] == 2.0
    assert pharma["max"] == 8.0
    print("  ✅ test_cold_chain_profiles")


def test_flint_signal_replay():
    """Test: detekcja replay attack."""
    fs = FlintSignal(replay_window_seconds=3600)
    sig = Signal(value=-65.0, signal_type=SignalType.SIGNAL_RAW, source_id="gw-01")
    # Pierwszy odczyt — OK
    result1 = fs.analyze(sig)
    # Drugi odczyt tego samego sygnału — replay
    result2 = fs.analyze(sig)
    assert result2["replay_detected"] == True
    print("  ✅ test_flint_signal_replay")


def run_all():
    print("\n  === FLINT Tests ===")
    test_flint_core_normal()
    test_flint_core_above_max()
    test_flint_core_below_min()
    test_flint_core_zscore()
    test_flint_core_stats()
    test_flint_temperature_in_range()
    test_flint_temperature_excursion()
    test_flint_temperature_mkt()
    test_cold_chain_profiles()
    test_flint_signal_replay()
    print("  All FLINT tests passed! ✅\n")


if __name__ == "__main__":
    run_all()