"""Sensor platform for HomeState."""

import logging
from datetime import timedelta

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_URL, DEFAULT_API_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeState sensors from a config entry."""
    api_url = entry.data.get(CONF_API_URL, DEFAULT_API_URL)

    coordinator = HomeStateCoordinator(hass, api_url)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        HomeStateSensor(coordinator, "current_room", "HomeState Current Room", "mdi:map-marker"),
        HomeStateSensor(coordinator, "house_mode", "HomeState House Mode", "mdi:home"),
        HomeStateBinarySensor(coordinator, "working", "HomeState Working", "mdi:laptop"),
        HomeStateBinarySensor(coordinator, "sleeping", "HomeState Sleeping", "mdi:sleep"),
    ]

    # Dynamic room occupancy sensors
    context = coordinator.data or {}
    rooms = context.get("rooms", {})
    for room in rooms:
        sensors.append(
            HomeStateBinarySensor(
                coordinator,
                f"room_{room}_occupancy",
                f"HomeState {room.title()} Occupancy",
                "mdi:account-check",
                room=room,
            )
        )

    async_add_entities(sensors)


class HomeStateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch context state from HomeState API."""

    def __init__(self, hass: HomeAssistant, api_url: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api_url = api_url.rstrip("/")

    async def _async_update_data(self) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/api/context") as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"API returned {resp.status}")
                    return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching context: {err}") from err


class HomeStateSensor(SensorEntity):
    """A HomeState text sensor."""

    def __init__(self, coordinator: HomeStateCoordinator, key: str, name: str, icon: str) -> None:
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"homestate_{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        if self._key == "current_room":
            return data.get("current_room")
        if self._key == "house_mode":
            return data.get("house_mode")
        return None

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class HomeStateBinarySensor(SensorEntity):
    """A HomeState binary sensor (working, sleeping, room occupancy)."""

    def __init__(
        self,
        coordinator: HomeStateCoordinator,
        key: str,
        name: str,
        icon: str,
        room: str | None = None,
    ) -> None:
        self.coordinator = coordinator
        self._key = key
        self._room = room
        self._attr_name = name
        self._attr_unique_id = f"homestate_{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None

        if self._room:
            rooms = data.get("rooms", {})
            rs = rooms.get(self._room, {})
            return "on" if rs.get("occupancy") else "off"

        activity = data.get("activity", {})
        if self._key == "working":
            return "on" if activity.get("working") else "off"
        if self._key == "sleeping":
            return "on" if activity.get("sleeping") else "off"
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._room:
            data = self.coordinator.data or {}
            rooms = data.get("rooms", {})
            rs = rooms.get(self._room, {})
            return {"confidence": rs.get("confidence", 0)}
        return None

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
