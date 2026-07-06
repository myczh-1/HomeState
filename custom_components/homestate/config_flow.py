"""Config flow for HomeState."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_ENTITIES, CONF_RUN_MODE, DEFAULT_RUN_MODE, DOMAIN

RUN_MODES = ["observe", "suggest", "auto"]


class HomeStateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="HomeState",
                data={},
                options={
                    CONF_RUN_MODE: user_input.get(CONF_RUN_MODE, DEFAULT_RUN_MODE),
                    CONF_ENTITIES: {},
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_RUN_MODE, default=DEFAULT_RUN_MODE): vol.In(RUN_MODES),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HomeStateOptionsFlow(config_entry)


class HomeStateOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entities = dict(config_entry.options.get(CONF_ENTITIES, {}))
        self._run_mode = config_entry.options.get(CONF_RUN_MODE, DEFAULT_RUN_MODE)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._run_mode = user_input[CONF_RUN_MODE]
            return await self.async_step_entity_list()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_RUN_MODE, default=self._run_mode): vol.In(RUN_MODES),
            }),
        )

    async def async_step_entity_list(self, user_input=None):
        if user_input is not None:
            action = user_input.get("action", "done")
            if action == "add":
                return await self.async_step_add_entity()
            if action == "remove":
                return await self.async_step_remove_entity()
            # Done — save
            return self.async_create_entry(
                title="HomeState",
                data={
                    CONF_RUN_MODE: self._run_mode,
                    CONF_ENTITIES: self._entities,
                },
            )

        # Show current mappings
        summary = self._build_summary()

        return self.async_show_form(
            step_id="entity_list",
            data_schema=vol.Schema({
                vol.Required("action", default="done"): vol.In({
                    "done": f"完成 (当前 {len(self._entities)} 个映射)",
                    "add": "添加传感器映射",
                    "remove": "删除传感器映射",
                }),
            }),
            description_placeholders={"summary": summary},
        )

    async def async_step_add_entity(self, user_input=None):
        if user_input is not None:
            entity_id = user_input["entity_id"]
            self._entities[entity_id] = {
                "room": user_input["room"],
                "semantic": user_input.get("semantic", "room_motion"),
                "confidence": user_input.get("confidence", 0.9),
            }
            return await self.async_step_entity_list()

        return self.async_show_form(
            step_id="add_entity",
            data_schema=vol.Schema({
                vol.Required("entity_id"): str,
                vol.Required("room"): str,
                vol.Optional("semantic", default="room_motion"): vol.In([
                    "room_motion", "desk_presence", "presence", "door",
                ]),
                vol.Optional("confidence", default=0.95): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                ),
            }),
        )

    async def async_step_remove_entity(self, user_input=None):
        if not self._entities:
            return await self.async_step_entity_list()

        if user_input is not None:
            entity_id = user_input["entity_id"]
            self._entities.pop(entity_id, None)
            return await self.async_step_entity_list()

        return self.async_show_form(
            step_id="remove_entity",
            data_schema=vol.Schema({
                vol.Required("entity_id"): vol.In(list(self._entities.keys())),
            }),
        )

    def _build_summary(self) -> str:
        if not self._entities:
            return "暂无语义映射。请添加你的传感器。"
        lines = []
        for eid, info in self._entities.items():
            lines.append(f"- {eid} → {info.get('room', '?')} ({info.get('semantic', '?')})")
        return "\n".join(lines)
