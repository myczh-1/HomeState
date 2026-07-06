"""AI Client — OpenAI-compatible interface for semantic mapping."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个智能家居语义映射助手。用户会描述他们的设备，你需要将这些设备映射到房间和语义类型。

语义类型（semantic）有以下几种：
- room_motion: 房间移动传感器，用于检测房间是否有人
- desk_presence: 书桌前有人，通常放在书桌下方
- presence: 人体存在传感器（毫米波等高精度传感器）
- door: 门传感器

房间名（room）用英文小写，如 study, bedroom, living_room, kitchen, bathroom 等。

你必须严格返回 JSON 数组，每个元素包含：
- entity_id: 实体ID（从提供的列表中匹配）
- room: 房间名
- semantic: 语义类型
- confidence: 置信度 0.0-1.0（默认0.9，毫米波传感器可给0.95）
- meaning: 语义含义数组（可选，如 ["user_at_computer", "working_indicator"]）

只返回 JSON，不要任何其他文字。"""


async def parse_entities(
    base_url: str,
    api_key: str,
    model: str,
    user_input: str,
    available_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Send user description + entity list to AI, get semantic mappings back."""
    entity_list = "\n".join(
        f"- {e['entity_id']} ({e.get('name', '')}) [{e.get('platform', '')}]"
        for e in available_entities
    )

    user_msg = f"""以下是用户 Home Assistant 中的设备列表：

{entity_list}

用户描述：
{user_input}

请根据用户描述，将相关设备映射为语义配置。"""

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
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
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    _LOGGER.error("AI API error %d: %s", resp.status, body)
                    return []

                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return _parse_json_response(content)

    except Exception as err:
        _LOGGER.error("AI request failed: %s", err)
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
