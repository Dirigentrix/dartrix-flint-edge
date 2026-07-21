"""
src/services/flint/flint_signal.py
------------------------------------
FLINT Signal — przetwarzanie i analiza sygnałów RF/komunikacyjnych.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import math
import statistics
from typing import List, Dict, Optional
from collections import deque
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType, SignalStatus
from domain.models import RiskLevel, Alert, AlertSeverity


class FlintSignal:
    """
    Moduł analizy sygnałów komunikacyjnych.
    Wykrywa: utratę sygnału, replay attacks, anomalie RSSI,
    zakłócenia i ataki na warstwę komunikacyjną.
    """

    RSSI_THRESHOLDS = {
        "excellent": (-60, 0),
        "good":      (-70, -60),
        "fair":      (-80, -70),
        "poor":      (-90, -80),
        "critical":  (-120, -90),
    }

    def __init__(self, replay_window_seconds: int = 30):
        self.replay_window = replay_window_seconds
        self._seen_signal_ids: deque = deque(maxlen=10000)
        self._seen_timestamps: deque = deque(maxlen=10000)
        self._rssi_history: deque = deque(maxlen=200)
        self.signals_analyzed: int = 0
        self.replay_attacks_detected: int = 0
        self.signal_losses: int = 0
        self.alerts: List[Alert] = []
        self._last_signal_time: Optional[datetime.datetime] = None

    def analyze(self, signal: Signal) -> Dict:
        """Analizuje sygnał komunikacyjny."""
        self.signals_analyzed += 1
        now = datetime.datetime.now()

        results = {
            "signal_id":       signal.signal_id,
            "source_id":       signal.source_id,
            "value":           signal.value,
            "ts":              signal.timestamp.isoformat(),
            "replay_detected": False,
            "signal_loss":     False,
            "rssi_quality":    "unknown",
            "risk_score":      0.0,
            "risk_level":      RiskLevel.NONE.label,
            "alerts":          [],
        }

        # 1. Replay attack detection
        replay = self._detect_replay(signal)
        if replay:
            self.replay_attacks_detected += 1
            results["replay_detected"] = True
            alert = Alert(
                severity = AlertSeverity.CRITICAL,
                title    = "Replay Attack Detected",
                message  = f"Signal {signal.signal_id[:8]} from {signal.source_id} appears to be replayed",
                source   = "flint_signal",
                tags     = ["security", "replay_attack", signal.source_id],
            )
            self.alerts.append(alert)
            results["alerts"].append(alert.to_dict())
            results["risk_score"] = 0.95
            results["risk_level"] = RiskLevel.CRITICAL.label

        # 2. Signal loss detection
        if self._last_signal_time:
            gap = (now - self._last_signal_time).total_seconds()
            if gap > 300:  # 5 minut bez sygnału
                self.signal_losses += 1
                results["signal_loss"] = True
                results["gap_seconds"] = round(gap, 1)
                alert = Alert(
                    severity = AlertSeverity.WARNING,
                    title    = "Signal Loss Detected",
                    message  = f"No signal from {signal.source_id} for {gap:.0f}s",
                    source   = "flint_signal",
                    tags     = ["signal_loss", signal.source_id],
                )
                self.alerts.append(alert)
                results["alerts"].append(alert.to_dict())

        # 3. RSSI quality (if value represents RSSI)
        if signal.signal_type == SignalType.SIGNAL_RAW:
            rssi = signal.value
            self._rssi_history.append(rssi)
            quality = self._classify_rssi(rssi)
            results["rssi_quality"] = quality
            results["rssi_dbm"] = rssi

            if quality == "critical":
                results["risk_score"] = max(results["risk_score"], 0.75)
                results["risk_level"] = RiskLevel.HIGH.label

        # 4. Update tracking
        self._seen_signal_ids.append(signal.signal_id)
        self._seen_timestamps.append(signal.timestamp)
        self._last_signal_time = now

        return results

    def _detect_replay(self, signal: Signal) -> bool:
        """Wykrywa replay attack na podstawie ID i timestampu."""
        # Sprawdź duplikat ID
        if signal.signal_id in self._seen_signal_ids:
            return True

        # Sprawdź stary timestamp
        age = (datetime.datetime.now() - signal.timestamp).total_seconds()
        if age > self.replay_window:
            return True

        return False

    def _classify_rssi(self, rssi: float) -> str:
        for quality, (min_r, max_r) in self.RSSI_THRESHOLDS.items():
            if min_r <= rssi <= max_r:
                return quality
        return "unknown"

    def rssi_stats(self) -> Dict:
        history = list(self._rssi_history)
        if not history:
            return {"count": 0}
        return {
            "count":  len(history),
            "mean":   round(statistics.mean(history), 2),
            "min":    round(min(history), 2),
            "max":    round(max(history), 2),
            "latest": round(history[-1], 2),
            "quality": self._classify_rssi(history[-1]),
        }

    def stats(self) -> Dict:
        return {
            "module":                   "FLINT Signal",
            "signals_analyzed":         self.signals_analyzed,
            "replay_attacks_detected":  self.replay_attacks_detected,
            "signal_losses":            self.signal_losses,
            "active_alerts":            len([a for a in self.alerts if not a.resolved]),
            "rssi_stats":               self.rssi_stats(),
        }