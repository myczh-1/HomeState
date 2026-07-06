"""Config flow for HomeState."""

from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .ai_client import parse_entities
from .const import (
    CONF_AI_API_KEY, CONF_AI_BASE_URL, CONF_AI_MODEL,
    CONF_ENTITIES, CONF_RUN_MODE,
    DEFAULT_AI_MODEL, DEFAULT_RUN_MODE, DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
RUN_MODES = ["observe", "suggest", "auto"]
SEMANTIC_TYPES = ["room_motion", "desk_presence", "presence", "door"]


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

    def __init__(self, config_entry):
        self._entities = dict(config_entry.options.get(CONF_ENTITIES, {}))
        self._run_mode = config_entry.options.get(CONF_RUN_MODE, DEFAULT_RUN_MODE)
        self._ai_url = config_entry.options.get(CONF_AI_BASE_URL, "")
        self._ai_key = config_entry.options.get(CONF_AI_API_KEY, "")
        self._ai_model = config_entry.options.get(CONF_AI_MODEL, DEFAULT_AI_MODEL)
        self._selected: list[str] = []
        self._ai_results: list[dict] = []

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._run_mode = user_input.get(CONF_RUN_MODE, self._run_mode)
            action = user_input.get("action", "done")
            if action == "ai_setup":
                return await self.async_step_ai_config()
            if action == "ai_add":
                return await self.async_step_select_devices()
            if action == "manual_add":
                return await self.async_step_manual_add()
            if action == "remove":
                return await self.async_step_remove()
            return self._save()

        has_ai = bool(self._ai_url and self._ai_key)
        choices = {"done": f"完成保存 ({len(self._entities)} 个映射)"}
        if has_ai:
            choices["ai_add"] = "AI 自然语言添加"
        else:
            choices["ai_setup"] = "配置 AI 接口"
        choices["manual_add"] = "手动添加映射"
        if self._entities:
            choices["remove"] = "删除映射"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_RUN_MODE, default=self._run_mode): vol.In(RUN_MODES),
                vol.Optional("action", default="done"): vol.In(choices),
            }),
            description_placeholders={"summary": self._build_summary()},
        )

    async def async_step_ai_config(self, user_input=None):
        if user_input is not None:
            self._ai_url = user_input.get(CONF_AI_BASE_URL, "")
            self._ai_key = user_input.get(CONF_AI_API_KEY, "")
            self._ai_model = user_input.get(CONF_AI_MODEL, DEFAULT_AI_MODEL)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="ai_config",
            data_schema=vol.Schema({
                vol.Required(CONF_AI_BASE_URL, default=self._ai_url or "https://api.openai.com"): str,
                vol.Required(CONF_AI_API_KEY, default=self._ai_key): str,
                vol.Optional(CONF_AI_MODEL, default=self._ai_model): str,
            }),
        )

    async def async_step_select_devices(self, user_input=None):
        if user_input is not None:
            self._selected = user_input.get("entities", [])
            if self._selected:
                return await self.async_step_describe()
            return await self.async_step_init()

        entity_map = self._get_entity_map()
        return self.async_show_form(
            step_id="select_devices",
            data_schema=vol.Schema({
                vol.Required("entities"): vol.All(list, vol.Length(min=1)),
            }),
            description_placeholders={
                "count": str(len(entity_map)),
                "hint": "选择要映射的传感器",
            },
        )

    async def async_step_describe(self, user_input=None):
        if user_input is not None:
            desc = user_input.get("description", "")
            if desc:
                return await self._call_ai(desc)
            return await self.async_step_init()

        device_list = "\n".join(f"- {eid}" for eid in self._selected)
        return self.async_show_form(
            step_id="describe",
            data_schema=vol.Schema({
                vol.Required("description"): str,
            }),
            description_placeholders={"devices": device_list},
        )

    async def async_step_review(self, user_input=None):
        if user_input is not None:
            action = user_input.get("action", "accept")
            if action == "accept":
                for item in self._ai_results:
                    eid = item.get("entity_id", "")
                    if eid:
                        self._entities[eid] = {
                            "room": item.get("room", ""),
                            "semantic": item.get("semantic", "room_motion"),
                            "confidence": item.get("confidence", 0.9),
                            "meaning": item.get("meaning", []),
                        }
                return await self.async_step_init()
            return await self.async_step_describe()

        lines = []
        for item in self._ai_results:
            eid = item.get("entity_id", "?")
            room = item.get("room", "?")
            sem = item.get("semantic", "?")
            conf = item.get("confidence", 0.9)
            lines.append(f"- {eid} -> {room} ({sem}, {conf})")
        summary = "\n".join(lines) if lines else "AI 未返回结果"

        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema({
                vol.Optional("action", default="accept"): vol.In({
                    "accept": "确认添加",
                    "retry": "重新描述",
                }),
            }),
            description_placeholders={"results": summary},
        )

    async def async_step_manual_add(self, user_input=None):
        if user_input is not None:
            eid = user_input["entity_id"]
            self._entities[eid] = {
                "room": user_input["room"],
                "semantic": user_input.get("semantic", "room_motion"),
                "confidence": user_input.get("confidence", 0.9),
                "meaning": [],
            }
            return await self.async_step_init()

        return self.async_show_form(
            step_id="manual_add",
            data_schema=vol.Schema({
                vol.Required("entity_id"): str,
                vol.Required("room"): str,
                vol.Optional("semantic", default="room_motion"): vol.In(SEMANTIC_TYPES),
                vol.Optional("confidence", default=0.95): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                ),
            }),
        )

    async def async_step_remove(self, user_input=None):
        if not self._entities:
            return await self.async_step_init()
        if user_input is not None:
            self._entities.pop(user_input["entity_id"], None)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema({
                vol.Required("entity_id"): vol.In(list(self._entities.keys())),
            }),
        )

    async def _call_ai(self, description: str):
        entity_map = self._get_entity_map()
        available = [
            {"entity_id": eid, "name": info.get("name", ""), "platform": info.get("platform", "")}
            for eid, info in entity_map.items()
            if eid in self._selected
        ]
        self._ai_results = await parse_entities(
            self._ai_url, self._ai_key, self._ai_model,
            description, available,
        )
        if self._ai_results:
            return await self.async_step_review()
        return self.async_show_form(
            step_id="describe",
            data_schema=vol.Schema({vol.Required("description"): str}),
            description_placeholders={"devices": "\n".join(f"- {e}" for e in self._selected)},
            errors={"description": "ai_no_result"},
        )

    def _get_entity_map(self) -> dict:
        states = self.hass.states.async_all()
        result = {}
        for state in states:
            eid = state.entity_id
            if eid.startswith(("sensor.", "binary_sensor.", "device_tracker.", "switch.", "light.")):
                result[eid] = {
                    "name": state.attributes.get("friendly_name", ""),
                    "platform": eid.split(".")[0],
                }
        return result

    def _build_summary(self) -> str:
        if not self._entities:
            return "暂无语义映射"
        lines = []
        for eid, info in self._entities.items():
            lines.append(f"- {eid} -> {info.get('room', '?')} ({info.get('semantic', '?')})")
        return "\n".join(lines)

    def _save(self):
        data = {
            CONF_RUN_MODE: self._run_mode,
            CONF_ENTITIES: self._entities,
            CONF_AI_BASE_URL: self._ai_url,
            CONF_AI_API_KEY: self._ai_key,
            CONF_AI_MODEL: self._ai_model,
        }
        return self.async_create_entry(title="HomeState", data=data)
