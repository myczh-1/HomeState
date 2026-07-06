"""Data models for HomeState."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RunMode(str, Enum):
    OBSERVE = "observe"
    SUGGEST = "suggest"
    AUTO = "auto"


class HouseMode(str, Enum):
    SINGLE = "single_person"
    MULTI = "multi_person"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass
class FactEvent:
    entity_id: str
    state: str
    old_state: str = ""
    attributes: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SemanticMapping:
    entity_id: str
    room: str
    semantic: str
    meaning: list[str] = field(default_factory=list)
    confidence: float = 0.9
    role: str = ""
    control_policy: str = ""


@dataclass
class RoomState:
    occupancy: bool = False
    confidence: float = 0.0
    last_motion: datetime | None = None
    activity: str = ""


@dataclass
class ActivityState:
    working: bool = False
    sleeping: bool = False


@dataclass
class ContextState:
    house_mode: str = "unknown"
    current_room: str = ""
    rooms: dict[str, RoomState] = field(default_factory=dict)
    activity: ActivityState = field(default_factory=ActivityState)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Decision:
    action: str
    entity: str
    allowed: bool = False
    confidence: float = 0.0
    reason: str = ""
    guardrails_passed: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
