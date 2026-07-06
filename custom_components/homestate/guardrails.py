"""Guardrails Engine — hard rules, no AI dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import ContextState


@dataclass
class RuleEffect:
    deny: list[str] = field(default_factory=list)
    set_mode: str = ""
    require_confirmation: bool = False


@dataclass
class TriggeredRule:
    rule_id: str
    effect: RuleEffect


class GuardrailsEngine:
    """Evaluates hard rules against context state."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, callable, RuleEffect]] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        self._rules = [
            (
                "night_no_auto_light",
                lambda ctx: self._is_night(),
                RuleEffect(deny=["auto_turn_on_main_light"]),
            ),
            (
                "multi_room_disable_auto",
                lambda ctx: sum(1 for r in ctx.rooms.values() if r.occupancy) >= 2,
                RuleEffect(set_mode="safe_mode"),
            ),
            (
                "low_confidence_block",
                lambda ctx: any(
                    r.occupancy and r.confidence < 0.75 for r in ctx.rooms.values()
                ),
                RuleEffect(require_confirmation=True),
            ),
        ]

    @staticmethod
    def _is_night() -> bool:
        now = datetime.now()
        t = now.hour * 60 + now.minute
        return t >= 23 * 60 + 30 or t < 7 * 60

    def evaluate(self, ctx: ContextState) -> list[TriggeredRule]:
        triggered = []
        for rule_id, condition, effect in self._rules:
            if condition(ctx):
                triggered.append(TriggeredRule(rule_id=rule_id, effect=effect))
        return triggered

    def is_allowed(self, ctx: ContextState, action: str) -> tuple[bool, str]:
        for tr in self.evaluate(ctx):
            if action in tr.effect.deny:
                return False, f"blocked by rule: {tr.rule_id}"
            if tr.effect.require_confirmation:
                return False, f"requires confirmation due to rule: {tr.rule_id}"
        return True, ""
