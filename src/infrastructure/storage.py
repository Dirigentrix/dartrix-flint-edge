"""
src/infrastructure/storage.py
------------------------------
Warstwa przechowywania danych — in-memory z opcją eksportu JSON.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import json
import os
from typing import List, Dict, Any, Optional
from collections import deque


class DataStorage:
    """
    Prosta warstwa przechowywania danych w pamięci.
    Obsługuje: sygnały, decyzje, alerty, telemetrię.
    Gotowa do zastąpienia przez PostgreSQL/TimescaleDB.
    """

    def __init__(self, max_records: int = 10_000,
                 export_dir: str = "logs"):
        self.max_records = max_records
        self.export_dir  = export_dir

        self._signals:   deque = deque(maxlen=max_records)
        self._decisions: deque = deque(maxlen=max_records)
        self._alerts:    deque = deque(maxlen=max_records)
        self._telemetry: deque = deque(maxlen=max_records)
        self._events:    deque = deque(maxlen=max_records)

        self._counts: Dict[str, int] = {
            "signals": 0, "decisions": 0,
            "alerts": 0, "telemetry": 0, "events": 0,
        }

    # ── STORE ─────────────────────────────────────────────────

    def store_signal(self, signal_dict: Dict):
        self._signals.append({**signal_dict, "_stored_at": datetime.datetime.now().isoformat()})
        self._counts["signals"] += 1

    def store_decision(self, decision_dict: Dict):
        self._decisions.append({**decision_dict, "_stored_at": datetime.datetime.now().isoformat()})
        self._counts["decisions"] += 1

    def store_alert(self, alert_dict: Dict):
        self._alerts.append({**alert_dict, "_stored_at": datetime.datetime.now().isoformat()})
        self._counts["alerts"] += 1

    def store_telemetry(self, telemetry_dict: Dict):
        self._telemetry.append({**telemetry_dict, "_stored_at": datetime.datetime.now().isoformat()})
        self._counts["telemetry"] += 1

    def store_event(self, event_type: str, data: Dict = None):
        self._events.append({
            "event_type": event_type,
            "data":       data or {},
            "ts":         datetime.datetime.now().isoformat(),
        })
        self._counts["events"] += 1

    # ── QUERY ─────────────────────────────────────────────────

    def get_signals(self, n: int = 100,
                    signal_type: str = None) -> List[Dict]:
        records = list(self._signals)
        if signal_type:
            records = [r for r in records if r.get("signal_type") == signal_type]
        return records[-n:]

    def get_decisions(self, n: int = 50,
                      status: str = None) -> List[Dict]:
        records = list(self._decisions)
        if status:
            records = [r for r in records if r.get("status") == status]
        return records[-n:]

    def get_alerts(self, n: int = 50,
                   resolved: bool = None) -> List[Dict]:
        records = list(self._alerts)
        if resolved is not None:
            records = [r for r in records if r.get("resolved") == resolved]
        return records[-n:]

    def get_telemetry(self, n: int = 100,
                      device_id: str = None) -> List[Dict]:
        records = list(self._telemetry)
        if device_id:
            records = [r for r in records if r.get("device_id") == device_id]
        return records[-n:]

    # ── EXPORT ────────────────────────────────────────────────

    def export_json(self, collection: str = "signals",
                    filename: str = None) -> str:
        """Eksportuje kolekcję do pliku JSON."""
        collections = {
            "signals":   list(self._signals),
            "decisions": list(self._decisions),
            "alerts":    list(self._alerts),
            "telemetry": list(self._telemetry),
            "events":    list(self._events),
        }
        data = collections.get(collection, [])

        if not filename:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{collection}_{ts}.json"

        os.makedirs(self.export_dir, exist_ok=True)
        filepath = os.path.join(self.export_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return filepath

    # ── STATS ─────────────────────────────────────────────────

    def stats(self) -> Dict:
        return {
            "stored_counts":  self._counts,
            "buffer_sizes": {
                "signals":   len(self._signals),
                "decisions": len(self._decisions),
                "alerts":    len(self._alerts),
                "telemetry": len(self._telemetry),
                "events":    len(self._events),
            },
            "max_records": self.max_records,
        }

    def clear(self, collection: str = "all"):
        """Czyści kolekcję lub wszystkie dane."""
        if collection == "all" or collection == "signals":
            self._signals.clear()
        if collection == "all" or collection == "decisions":
            self._decisions.clear()
        if collection == "all" or collection == "alerts":
            self._alerts.clear()
        if collection == "all" or collection == "telemetry":
            self._telemetry.clear()
        if collection == "all" or collection == "events":
            self._events.clear()