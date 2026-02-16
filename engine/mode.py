from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
import logging


class TradingMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass
class ModeChangeEvent:
    from_mode: TradingMode
    to_mode: TradingMode
    reason: str


class ModeManager:
    def __init__(self, initial_mode: TradingMode = TradingMode.PAPER):
        self._mode = initial_mode
        self.logger = logging.getLogger("mode_manager")

    @property
    def mode(self) -> TradingMode:
        return self._mode

    def switch_mode(
        self,
        target_mode: TradingMode,
        has_open_position: bool,
        confirm_live: bool = False,
        auth_validator: Optional[Callable[[], bool]] = None,
    ) -> ModeChangeEvent:
        if target_mode == self._mode:
            return ModeChangeEvent(self._mode, target_mode, "No-op switch request")

        if has_open_position:
            raise ValueError("Mode switch blocked: open position exists")

        if target_mode == TradingMode.LIVE:
            if not confirm_live:
                raise ValueError("LIVE switch requires confirmation")
            if auth_validator and not auth_validator():
                raise ValueError("LIVE switch blocked: Fyers authentication invalid")
            self.logger.warning("🚨🚨 LIVE MODE ACTIVATED - REAL CAPITAL AT RISK 🚨🚨")

        event = ModeChangeEvent(self._mode, target_mode, "User initiated")
        self._mode = target_mode
        self.logger.info(
            "MODE_SWITCH from=%s to=%s reason=%s",
            event.from_mode,
            event.to_mode,
            event.reason,
        )
        return event
