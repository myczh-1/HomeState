"""HomeState Coordinator — wires HA events to the context engine."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_ENTITIES, CONF_RUN_MODE, DEFAULT_RUN_MODE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .context import ContextEngine
from .decision import DecisionEngine
from .facts import FactsStore
from .guardrails import GuardrailsEngine
from .models import FactEvent, RunMode
from .semantic import SemanticRegistry

_LOGGER = logging.getLogger(__name__)


class HomeStateCoordinator(DataUpdateCoordinator):
    """Coordinates the HomeState context engine with HA events."""

    def __init__(self, hass: HomeAssistant, entry_id: str, options: dict) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # event-driven
        )
        self.entry_id = entry_id

        # Initialize layers
        self.facts = FactsStore()
        self.semantic = SemanticRegistry()
        self.context = ContextEngine()
        self.guardrails = GuardrailsEngine()

        run_mode = RunMode(options.get(CONF_RUN_MODE, DEFAULT_RUN_MODE))
        self.decision = DecisionEngine(
            self.context, self.guardrails, self.semantic, run_mode
        )

        # Load semantic mappings from options
        entities = options.get(CONF_ENTITIES, {})
        if entities:
            self.semantic.load_from_dict(entities)

    async def async_start(self) -> None:
        """Subscribe to HA state changes and start tick loop."""
        # Subscribe to state_changed events
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_changed)

        # Periodic tick for confidence decay
        async def _tick_loop():
            while True:
                await self.hass.async_add_executor_job(self.context.tick)
                self.async_set_updated_data(self.context.state)
                await self._async_sleep(DEFAULT_SCAN_INTERVAL)

        import asyncio
        self._tick_task = asyncio.create_task(_tick_loop())

        _LOGGER.info(
            "HomeState started: %d semantic mappings, mode=%s",
            len(self.semantic.all()),
            self.decision.mode.value,
        )

    @staticmethod
    async def _async_sleep(seconds: int) -> None:
        import asyncio
        await asyncio.sleep(seconds)

    @callback
    def _handle_state_changed(self, event: Event) -> None:
        """Process a state_changed event from HA."""
        entity_id = event.data.get("entity_id", "")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if new_state is None:
            return

        fact = FactEvent(
            entity_id=entity_id,
            state=new_state.state,
            old_state=old_state.state if old_state else "",
            attributes=dict(new_state.attributes) if new_state.attributes else {},
            timestamp=datetime.now(),
        )

        self.facts.record(fact)
        sem = self.semantic.get(entity_id)
        if sem is not None:
            self.context.process_fact(fact, sem)
            # Notify sensors to update
            self.async_set_updated_data(self.context.state)

    async def async_update_semantic(self, entity_id: str, mapping: dict) -> None:
        """Add or update a semantic mapping at runtime."""
        from .models import SemanticMapping

        self.semantic.set(SemanticMapping(
            entity_id=entity_id,
            room=mapping.get("room", ""),
            semantic=mapping.get("semantic", "room_motion"),
            meaning=mapping.get("meaning", []),
            confidence=mapping.get("confidence", 0.9),
            role=mapping.get("role", ""),
            control_policy=mapping.get("control_policy", ""),
        ))
        # Persist to config entry options
        new_options = {**self.config_entry.options}
        entities = new_options.get(CONF_ENTITIES, {})
        entities[entity_id] = mapping
        new_options[CONF_ENTITIES] = entities
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=new_options
        )

    def set_run_mode(self, mode: str) -> None:
        self.decision.mode = RunMode(mode)
