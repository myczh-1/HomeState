"""Sensor platform for HomeState."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeStateCoordinator
from .models import ContextState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HomeStateCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.context.state

    entities: list[SensorEntity] = [
        HomeStateCurrentRoomSensor(coordinator),
        HomeStateHouseModeSensor(coordinator),
        HomeStateActivitySensor(coordinator, "working", "HomeState Working", "mdi:laptop"),
        HomeStateActivitySensor(coordinator, "sleeping", "HomeState Sleeping", "mdi:sleep"),
    ]

    # Per-room occupancy sensors
    for room in list(state.rooms.keys()) + _get_rooms_from_options(entry):
        entities.append(HomeStateRoomOccupancySensor(coordinator, room))

    async_add_entities(entities)


def _get_rooms_from_options(entry: ConfigEntry) -> list[str]:
    rooms = set()
    for info in entry.options.get("entities", {}).values():
        room = info.get("room", "")
        if room:
            rooms.add(room)
    return list(rooms)


class HomeStateBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator: HomeStateCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def _ctx(self) -> ContextState:
        return self.coordinator.data or self.coordinator.context.state


class HomeStateCurrentRoomSensor(HomeStateBaseSensor):
    _attr_name = "HomeState Current Room"
    _attr_unique_id = "homestate_current_room"
    _attr_icon = "mdi:map-marker"

    @property
    def native_value(self) -> str | None:
        return self._ctx.current_room or None


class HomeStateHouseModeSensor(HomeStateBaseSensor):
    _attr_name = "HomeState House Mode"
    _attr_unique_id = "homestate_house_mode"
    _attr_icon = "mdi:home"

    @property
    def native_value(self) -> str | None:
        return self._ctx.house_mode or None


class HomeStateActivitySensor(HomeStateBaseSensor):
    def __init__(
        self, coordinator: HomeStateCoordinator, key: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"homestate_{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> str:
        activity = self._ctx.activity
        if self._key == "working":
            return "on" if activity.working else "off"
        if self._key == "sleeping":
            return "on" if activity.sleeping else "off"
        return "off"


class HomeStateRoomOccupancySensor(HomeStateBaseSensor):
    def __init__(self, coordinator: HomeStateCoordinator, room: str) -> None:
        super().__init__(coordinator)
        self._room = room
        self._attr_name = f"HomeState {room.replace('_', ' ').title()} Occupancy"
        self._attr_unique_id = f"homestate_{room}_occupancy"
        self._attr_icon = "mdi:account-check"

    @property
    def native_value(self) -> str:
        rs = self._ctx.rooms.get(self._room)
        if rs is None:
            return "off"
        return "on" if rs.occupancy else "off"

    @property
    def extra_state_attributes(self) -> dict | None:
        rs = self._ctx.rooms.get(self._room)
        if rs is None:
            return None
        return {
            "confidence": round(rs.confidence, 2),
            "last_motion": rs.last_motion.isoformat() if rs.last_motion else None,
        }
