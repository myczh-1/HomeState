"""Context Engine — maintains home state from facts + semantics."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import (
    ActivityState,
    ContextState,
    FactEvent,
    HouseMode,
    RoomState,
    SemanticMapping,
)

MOTION_TIMEOUT = timedelta(minutes=5)
CONFIDENCE_DECAY_PER_MINUTE = 0.02


class ContextEngine:
    """Maintains the current home context state."""

    def __init__(self) -> None:
        self._state = ContextState()

    @property
    def state(self) -> ContextState:
        return self._state

    def process_fact(self, event: FactEvent, sem: SemanticMapping | None) -> None:
        """Update context based on a new fact event."""
        if sem is None:
            return

        room = sem.room
        if room not in self._state.rooms:
            self._state.rooms[room] = RoomState()

        rs = self._state.rooms[room]

        if sem.semantic in ("desk_presence", "room_motion", "presence"):
            if event.state in ("on", "detected", "occupied"):
                rs.occupancy = True
                rs.confidence = 0.95
                rs.last_motion = event.timestamp
                if sem.semantic == "desk_presence":
                    self._state.activity.working = True
            elif event.state in ("off", "clear", "not_occupied"):
                rs.last_motion = event.timestamp
        elif sem.semantic == "door":
            rs.last_motion = event.timestamp

        self._state.rooms[room] = rs
        self._recalculate()
        self._state.updated_at = datetime.now()

    def tick(self) -> None:
        """Periodic maintenance: decay confidence, mark rooms empty."""
        now = datetime.now()

        for room, rs in self._state.rooms.items():
            if rs.occupancy and rs.last_motion:
                elapsed = now - rs.last_motion
                if elapsed > MOTION_TIMEOUT:
                    rs.occupancy = False
                    rs.confidence = 0.3
                else:
                    minutes = elapsed.total_seconds() / 60
                    rs.confidence = max(0.0, 0.95 - minutes * CONFIDENCE_DECAY_PER_MINUTE)
                self._state.rooms[room] = rs

        self._recalculate()
        self._state.updated_at = now

    def _recalculate(self) -> None:
        occupied = [r for r in self._state.rooms.values() if r.occupancy]

        if not occupied:
            self._state.house_mode = HouseMode.EMPTY.value
            self._state.current_room = ""
            self._state.activity.working = False
            self._state.activity.sleeping = False
            return

        # Find highest-confidence occupied room
        best_room = ""
        best_conf = 0.0
        for name, rs in self._state.rooms.items():
            if rs.occupancy and rs.confidence > best_conf:
                best_conf = rs.confidence
                best_room = name

        self._state.current_room = best_room
        self._state.house_mode = (
            HouseMode.SINGLE.value if len(occupied) == 1 else HouseMode.MULTI.value
        )

        # Sleeping heuristic: only bedroom occupied, not working
        bedroom = self._state.rooms.get("bedroom")
        if (
            bedroom
            and bedroom.occupancy
            and not self._state.activity.working
            and len(occupied) == 1
        ):
            self._state.activity.sleeping = True

    def set_room_state(self, room: str, rs: RoomState) -> None:
        self._state.rooms[room] = rs
        self._recalculate()
        self._state.updated_at = datetime.now()
