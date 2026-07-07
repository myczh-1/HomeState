"""AI Client — OpenAI-compatible interface for semantic mapping."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个智能家居语义映射助手。根据设备列表中的信息（名称、设备类型、区域），自动推断每个设备的房间和语义类型。

推断规则：
1. 根据 friendly_name 中的关键词判断房间和用途（如"书房"→study，"卧室"→bedroom，"大门"→door）
2. 根据 device_class 判断设备类型（door/window→door，motion→room_motion，occupancy→presence）
3. 根据 area（HA 已配置的区域）辅助判断房间
4. 如果设备信息不足以判断，confidence 设为 0.5 以下

语义类型（semantic）：
- room_motion: 房间级移动传感器
- desk_presence: 书桌区域人体存在
- presence: 高精度人体存在传感器（毫米波等）
- door: 门窗传感器

房间名（room）用英文小写，如 study, bedroom, living_room, kitchen, bathroom 等。中文房间名需翻译。

返回 JSON 数组，每个元素：
- entity_id: 实体ID
- friendly_name: 实体友好名称（原样返回）
- room: 房间名
- semantic: 语义类型
- confidence: 置信度 0.0-1.0
- meaning: 语义含义数组（可选）

只返回 JSON 数组，无其他文字。"""



async def parse_entities(
    base_url: str,
    api_key: str,
    model: str,
    available_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Auto-map entities to semantic config using AI."""
    def _fmt_entity(e: dict) -> str:
        parts = [f"- {e['entity_id']}"]
        name = e.get("name", "")
        if name:
            parts.append(f"  名称: {name}")
        dc = e.get("device_class", "")
        if dc:
            parts.append(f"  类型: {dc}")
        area = e.get("area", "")
        if area:
            parts.append(f"  区域: {area}")
        return "\n".join(parts)

    entity_list = "\n".join(_fmt_entity(e) for e in available_entities)

    user_msg = f"""以下是用户 Home Assistant 中的所有设备：

{entity_list}

请自动识别每个设备的房间和语义类型，返回映射结果。"""

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    _LOGGER.debug("AI request: url=%s, model=%s, entities=%d", url, model, len(available_entities))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
    }

    try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120, connect=10)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    _LOGGER.error("AI API error %d: %s", resp.status, body)
                    return []

                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return _parse_json_response(content)

    except Exception as err:
        _LOGGER.error("AI request failed: %s", repr(err), exc_info=True)
        return []


def _parse_json_response(content: str) -> list[dict[str, Any]]:
    """Extract JSON array from AI response, handling markdown code blocks."""
    content = content.strip()
    # Strip markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        # Try to find JSON array in the text
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass

    _LOGGER.warning("Failed to parse AI response: %s", content[:200])
    return []
