"""
src/infrastructure/logging.py
------------------------------
System logowania DARTRIX FLINT EDGE.
DARTRIX FLINT EDGE v0.9 RC
"""

import datetime
import json
import os
from enum import Enum
from typing import List, Dict, Any, Optional
from collections import deque


class LogLevel(Enum):
    DEBUG   = 0
    INFO    = 1
    WARNING = 2
    ERROR   = 3
    CRITICAL= 4


class LogEntry:
    """Pojedynczy wpis logu."""

    def __init__(self, level: LogLevel, module: str,
                 message: str, data: Dict = None):
        self.timestamp = datetime.datetime.now()
        self.level     = level
        self.module    = module
        self.message   = message
        self.data      = data or {}

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level":     self.level.name,
            "module":    self.module,
            "message":   self.message,
            "data":      self.data,
        }

    def format(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] [{self.level.name:8s}] [{self.module:20s}] {self.message}"


class SystemLogger:
    """
    System logowania — buforuje logi w pamięci i opcjonalnie zapisuje do pliku.
    """

    LEVEL_COLORS = {
        LogLevel.DEBUG:    "\033[37m",   # szary
        LogLevel.INFO:     "\033[36m",   # cyan
        LogLevel.WARNING:  "\033[33m",   # żółty
        LogLevel.ERROR:    "\033[31m",   # czerwony
        LogLevel.CRITICAL: "\033[35m",   # fioletowy
    }
    RESET = "\033[0m"

    def __init__(self, module: str = "system",
                 min_level: LogLevel = LogLevel.INFO,
                 buffer_size: int = 5000,
                 log_dir: str = "logs",
                 colorize: bool = True):
        self.module     = module
        self.min_level  = min_level
        self.colorize   = colorize
        self.log_dir    = log_dir
        self._buffer: deque = deque(maxlen=buffer_size)
        self._file_handle = None
        self._counts: Dict[str, int] = {l.name: 0 for l in LogLevel}

    # ── LOG METHODS ───────────────────────────────────────────

    def debug(self, msg: str, data: Dict = None):
        self._log(LogLevel.DEBUG, msg, data)

    def info(self, msg: str, data: Dict = None):
        self._log(LogLevel.INFO, msg, data)

    def warning(self, msg: str, data: Dict = None):
        self._log(LogLevel.WARNING, msg, data)

    def error(self, msg: str, data: Dict = None):
        self._log(LogLevel.ERROR, msg, data)

    def critical(self, msg: str, data: Dict = None):
        self._log(LogLevel.CRITICAL, msg, data)

    # ── QUERY ─────────────────────────────────────────────────

    def get_recent(self, n: int = 50,
                   min_level: LogLevel = None) -> List[Dict]:
        entries = list(self._buffer)
        if min_level:
            entries = [e for e in entries if e.level.value >= min_level.value]
        return [e.to_dict() for e in entries[-n:]]

    def get_errors(self, n: int = 20) -> List[Dict]:
        return self.get_recent(n, LogLevel.ERROR)

    def stats(self) -> Dict:
        return {
            "module":       self.module,
            "buffer_size":  len(self._buffer),
            "counts":       self._counts,
            "min_level":    self.min_level.name,
        }

    # ── PRIVATE ───────────────────────────────────────────────

    def _log(self, level: LogLevel, message: str, data: Dict = None):
        if level.value < self.min_level.value:
            return

        entry = LogEntry(level, self.module, message, data)
        self._buffer.append(entry)
        self._counts[level.name] = self._counts.get(level.name, 0) + 1

        # Console output
        formatted = entry.format()
        if self.colorize:
            color = self.LEVEL_COLORS.get(level, "")
            print(f"{color}{formatted}{self.RESET}")
        else:
            print(formatted)

    def child(self, module: str) -> "SystemLogger":
        """Tworzy logger potomny dla podmodułu."""
        child = SystemLogger(
            module    = f"{self.module}.{module}",
            min_level = self.min_level,
            colorize  = self.colorize,
        )
        return child