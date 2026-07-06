"""Semantic Layer — entity to room/meaning mapping."""

from __future__ import annotations

from .models import SemanticMapping


class SemanticRegistry:
    """Maps HA entities to human-readable semantics."""

    def __init__(self) -> None:
        self._mappings: dict[str, SemanticMapping] = {}

    def set(self, mapping: SemanticMapping) -> None:
        self._mappings[mapping.entity_id] = mapping

    def get(self, entity_id: str) -> SemanticMapping | None:
        return self._mappings.get(entity_id)

    def remove(self, entity_id: str) -> None:
        self._mappings.pop(entity_id, None)

    def all(self) -> list[SemanticMapping]:
        return list(self._mappings.values())

    def room_entities(self, room: str) -> list[str]:
        return [m.entity_id for m in self._mappings.values() if m.room == room]

    def load_from_dict(self, data: dict) -> None:
        """Load mappings from config entry options dict."""
        for entity_id, info in data.items():
            self._mappings[entity_id] = SemanticMapping(
                entity_id=entity_id,
                room=info.get("room", ""),
                semantic=info.get("semantic", "room_motion"),
                meaning=info.get("meaning", []),
                confidence=info.get("confidence", 0.9),
                role=info.get("role", ""),
                control_policy=info.get("control_policy", ""),
            )

    def to_dict(self) -> dict:
        """Export as dict for config entry storage."""
        return {
            eid: {
                "room": m.room,
                "semantic": m.semantic,
                "meaning": m.meaning,
                "confidence": m.confidence,
                "role": m.role,
                "control_policy": m.control_policy,
            }
            for eid, m in self._mappings.items()
        }
