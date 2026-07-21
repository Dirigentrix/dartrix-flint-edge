"""
src/infrastructure/config.py
-----------------------------
Konfiguracja systemu DARTRIX FLINT EDGE.
DARTRIX FLINT EDGE v0.9 RC
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class FlintConfig:
    window_size:  int   = 50
    sensitivity:  float = 2.5
    temp_profile: str   = "pharma"


@dataclass
class TESConfig:
    auto_execute: bool = True


@dataclass
class WolfConfig:
    auto_block:          bool = True
    max_failed_attempts: int  = 5
    block_duration_min:  int  = 30
    dedup_window_sec:    int  = 300


@dataclass
class DashboardConfig:
    host:        str  = "0.0.0.0"
    port:        int  = 8080
    debug:       bool = False
    refresh_sec: int  = 5


@dataclass
class SystemConfig:
    """Główna konfiguracja systemu."""

    environment: str           = "development"
    log_level:   str           = "INFO"
    version:     str           = "0.9-RC"

    flint:     FlintConfig     = field(default_factory=FlintConfig)
    tes:       TESConfig       = field(default_factory=TESConfig)
    wolf:      WolfConfig      = field(default_factory=WolfConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)

    # Dodatkowe ustawienia
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Tworzy konfigurację z zmiennych środowiskowych."""
        cfg = cls()
        cfg.environment = os.getenv("DARTRIX_ENV", "development")
        cfg.log_level   = os.getenv("DARTRIX_LOG_LEVEL", "INFO")
        cfg.flint.temp_profile = os.getenv("DARTRIX_TEMP_PROFILE", "pharma")
        cfg.dashboard.port = int(os.getenv("DARTRIX_DASHBOARD_PORT", "8080"))
        return cfg

    @classmethod
    def development(cls) -> "SystemConfig":
        cfg = cls()
        cfg.environment = "development"
        cfg.log_level   = "DEBUG"
        cfg.dashboard.debug = True
        return cfg

    @classmethod
    def production(cls) -> "SystemConfig":
        cfg = cls()
        cfg.environment = "production"
        cfg.log_level   = "WARNING"
        cfg.tes.auto_execute = False  # Wymaga zatwierdzenia w produkcji
        cfg.dashboard.debug = False
        return cfg

    def to_dict(self) -> Dict:
        return {
            "environment": self.environment,
            "log_level":   self.log_level,
            "version":     self.version,
            "flint": {
                "window_size":  self.flint.window_size,
                "sensitivity":  self.flint.sensitivity,
                "temp_profile": self.flint.temp_profile,
            },
            "tes": {
                "auto_execute": self.tes.auto_execute,
            },
            "wolf": {
                "auto_block":          self.wolf.auto_block,
                "max_failed_attempts": self.wolf.max_failed_attempts,
                "block_duration_min":  self.wolf.block_duration_min,
            },
            "dashboard": {
                "host":        self.dashboard.host,
                "port":        self.dashboard.port,
                "debug":       self.dashboard.debug,
                "refresh_sec": self.dashboard.refresh_sec,
            },
        }