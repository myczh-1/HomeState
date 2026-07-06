"""Decision Layer — action decisions based on context + guardrails."""

from __future__ import annotations

from .context import ContextEngine
from .guardrails import GuardrailsEngine
from .models import Decision, RunMode
from .semantic import SemanticRegistry


class DecisionEngine:
    """Makes action decisions."""

    def __init__(
        self,
        ctx: ContextEngine,
        guard: GuardrailsEngine,
        sem: SemanticRegistry,
        mode: RunMode = RunMode.OBSERVE,
    ) -> None:
        self._ctx = ctx
        self._guard = guard
        self._sem = sem
        self._mode = mode

    @property
    def mode(self) -> RunMode:
        return self._mode

    @mode.setter
    def mode(self, value: RunMode) -> None:
        self._mode = value

    def should_act(self, action: str, entity_id: str) -> Decision:
        ctx = self._ctx.state
        dec = Decision(action=action, entity=entity_id)

        sem = self._sem.get(entity_id)
        if sem is None:
            dec.allowed = False
            dec.reason = "no semantic mapping for entity"
            return dec

        room_state = ctx.rooms.get(sem.room)
        room_confidence = room_state.confidence if room_state else 0.0

        # Check guardrails
        allowed, reason = self._guard.is_allowed(ctx, action)
        dec.guardrails_passed = allowed

        if not allowed:
            dec.allowed = False
            dec.reason = reason
            dec.confidence = room_confidence
            return dec

        if self._mode == RunMode.OBSERVE:
            dec.allowed = False
            dec.reason = "observe mode — context updated but no action taken"
            dec.confidence = room_confidence
            return dec

        if self._mode == RunMode.SUGGEST:
            dec.allowed = False
            dec.reason = "suggested — awaiting user confirmation"
            dec.confidence = room_confidence
            return dec

        # Auto mode
        dec.allowed = True
        dec.confidence = room_confidence
        dec.reason = self._build_reason(ctx, sem.room, room_state)
        return dec

    @staticmethod
    def _build_reason(ctx, room: str, room_state) -> str:
        if room_state and room_state.occupancy:
            return f"{room} occupied (confidence: {room_state.confidence:.2f})"
        return f"{room} unoccupied (confidence: {room_state.confidence:.2f})"
