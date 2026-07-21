"""
src/services/flint/flint_core.py
---------------------------------
FLINT Core — główny moduł przetwarzania sygnałów i detekcji anomalii.
DARTRIX FLINT EDGE v0.9 RC

FLINT = Fast Lightweight INtelligent Telemetry
"""

import datetime
import statistics
from typing import List, Dict, Optional, Tuple
from collections import deque

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))

from domain.signal import Signal, SignalType, SignalStatus
from domain.models import RiskLevel, Alert, AlertSeverity


class FlintCore:
    """
    Główny silnik FLINT — przetwarza sygnały, wykrywa anomalie,
    oblicza ryzyko i generuje alerty.
    """

    VERSION = "0.9-RC"

    # Domyślne progi anomalii
    DEFAULT_THRESHOLDS = {
        SignalType.TEMPERATURE: {"min": -25.0, "max": 8.0,  "unit": "°C"},
        SignalType.HUMIDITY:    {"min": 20.0,  "max": 95.0, "unit": "%"},
        SignalType.PRESSURE:    {"min": 900.0, "max": 1100.0,"unit": "hPa"},
        SignalType.CO2:         {"min": 0.0,   "max": 5000.0,"unit": "ppm"},
        SignalType.VIBRATION:   {"min": 0.0,   "max": 2.0,  "unit": "g"},
    }

    def __init__(self, window_size: int = 50, sensitivity: float = 2.5):
        """
        Args:
            window_size:  Rozmiar okna historii sygnałów (dla Z-score)
            sensitivity:  Próg Z-score dla detekcji anomalii
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)

        # Bufory historii per typ sygnału
        self._history: Dict[SignalType, deque] = {
            st: deque(maxlen=window_size) for st in SignalType
        }

        # Statystyki
        self.signals_processed: int = 0
        self.anomalies_detected: int = 0
        self.alerts: List[Alert] = []
        self.started_at = datetime.datetime.now()

    # ── PUBLIC API ────────────────────────────────────────────

    def process(self, signal: Signal) -> Dict:
        """
        Przetwarza pojedynczy sygnał.

        Returns:
            dict z wynikiem przetwarzania: is_anomaly, risk_score, alert
        """
        self.signals_processed += 1

        # 1. Walidacja
        if not signal.validate():
            signal.status = SignalStatus.REJECTED
            return self._result(signal, False, 0.0, "rejected: invalid signal")

        # 2. Sprawdzenie progów
        threshold_breach, breach_msg = self._check_thresholds(signal)

        # 3. Detekcja anomalii Z-score
        zscore_anomaly, z_score = self._check_zscore(signal)

        # 4. Aktualizacja historii
        self._history[signal.signal_type].append(signal.value)

        # 5. Obliczenie risk score
        risk_score = self._calculate_risk(signal, threshold_breach, z_score)
        risk_level = RiskLevel.from_score(risk_score)

        # 6. Oznaczenie anomalii
        is_anomaly = threshold_breach or zscore_anomaly
        if is_anomaly:
            self.anomalies_detected += 1
            signal.mark_anomaly(breach_msg or f"Z-score={z_score:.2f}")
        else:
            signal.status = SignalStatus.PROCESSED

        # 7. Generowanie alertu
        alert = None
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            alert = self._create_alert(signal, risk_level, breach_msg or f"Z={z_score:.2f}")
            self.alerts.append(alert)

        return self._result(signal, is_anomaly, risk_score, breach_msg,
                            z_score, risk_level, alert)

    def process_batch(self, signals: List[Signal]) -> List[Dict]:
        """Przetwarza listę sygnałów."""
        return [self.process(s) for s in signals]

    def set_threshold(self, signal_type: SignalType,
                      min_val: float = None, max_val: float = None):
        """Ustawia progi dla danego typu sygnału."""
        if signal_type not in self.thresholds:
            self.thresholds[signal_type] = {"min": None, "max": None, "unit": ""}
        if min_val is not None:
            self.thresholds[signal_type]["min"] = min_val
        if max_val is not None:
            self.thresholds[signal_type]["max"] = max_val

    def get_history(self, signal_type: SignalType) -> List[float]:
        """Zwraca historię wartości dla danego typu sygnału."""
        return list(self._history[signal_type])

    def stats(self) -> Dict:
        """Zwraca statystyki modułu FLINT."""
        uptime = (datetime.datetime.now() - self.started_at).total_seconds()
        return {
            "module":             "FLINT Core",
            "version":            self.VERSION,
            "signals_processed":  self.signals_processed,
            "anomalies_detected": self.anomalies_detected,
            "anomaly_rate":       round(self.anomalies_detected /
                                        max(1, self.signals_processed), 4),
            "active_alerts":      len([a for a in self.alerts if not a.resolved]),
            "total_alerts":       len(self.alerts),
            "uptime_seconds":     round(uptime, 1),
            "window_size":        self.window_size,
            "sensitivity":        self.sensitivity,
        }

    # ── PRIVATE ───────────────────────────────────────────────

    def _check_thresholds(self, signal: Signal) -> Tuple[bool, str]:
        """Sprawdza czy wartość przekracza progi."""
        thresh = self.thresholds.get(signal.signal_type)
        if not thresh:
            return False, ""

        val = signal.value
        unit = thresh.get("unit", "")

        if thresh.get("min") is not None and val < thresh["min"]:
            return True, f"Below min: {val}{unit} < {thresh['min']}{unit}"
        if thresh.get("max") is not None and val > thresh["max"]:
            return True, f"Above max: {val}{unit} > {thresh['max']}{unit}"
        return False, ""

    def _check_zscore(self, signal: Signal) -> Tuple[bool, float]:
        """Wykrywa anomalie metodą Z-score."""
        history = list(self._history[signal.signal_type])
        if len(history) < 5:
            return False, 0.0

        mean = statistics.mean(history)
        try:
            stdev = statistics.stdev(history)
        except statistics.StatisticsError:
            return False, 0.0

        if stdev == 0:
            return False, 0.0

        z = abs((signal.value - mean) / stdev)
        return z > self.sensitivity, round(z, 3)

    def _calculate_risk(self, signal: Signal, threshold_breach: bool,
                        z_score: float) -> float:
        """Oblicza wynik ryzyka (0.0–1.0)."""
        score = 0.0

        # Naruszenie progu
        if threshold_breach:
            thresh = self.thresholds.get(signal.signal_type, {})
            min_v = thresh.get("min")
            max_v = thresh.get("max")
            if min_v is not None and max_v is not None:
                range_v = max_v - min_v
                if range_v > 0:
                    deviation = max(
                        max(0, min_v - signal.value),
                        max(0, signal.value - max_v)
                    )
                    score += min(0.7, deviation / range_v)
            else:
                score += 0.5

        # Z-score contribution
        if z_score > 0:
            score += min(0.3, z_score / (self.sensitivity * 3))

        return round(min(1.0, score), 4)

    def _create_alert(self, signal: Signal, risk_level: RiskLevel,
                      reason: str) -> Alert:
        """Tworzy alert dla anomalii."""
        severity = (AlertSeverity.CRITICAL
                    if risk_level == RiskLevel.CRITICAL
                    else AlertSeverity.ERROR)
        return Alert(
            severity = severity,
            title    = f"FLINT Anomaly: {signal.signal_type.value}",
            message  = f"Signal {signal.signal_id[:8]} from {signal.source_id}: {reason}",
            source   = "flint_core",
            metadata = {"signal": signal.to_dict(), "risk_level": risk_level.label},
            tags     = ["flint", signal.signal_type.value, risk_level.label.lower()],
        )

    def _result(self, signal: Signal, is_anomaly: bool, risk_score: float,
                reason: str = "", z_score: float = 0.0,
                risk_level: RiskLevel = RiskLevel.NONE,
                alert: Optional[Alert] = None) -> Dict:
        return {
            "signal_id":   signal.signal_id,
            "signal_type": signal.signal_type.value,
            "value":       signal.value,
            "status":      signal.status.value,
            "is_anomaly":  is_anomaly,
            "risk_score":  risk_score,
            "risk_level":  risk_level.label,
            "z_score":     z_score,
            "reason":      reason,
            "alert":       alert.to_dict() if alert else None,
            "ts":          signal.timestamp.isoformat(),
        }