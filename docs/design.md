# HomeState 设计文档

> HomeState 是 Home Assistant 的自定义集成，在现有智能家居之上引入家庭上下文层（Home Context Layer）。
> 不替代 HA 自动化系统，而是在其上增加一层"语义理解 + 状态推理 + 虚拟传感器"的认知层。

## 项目定位

HA 现有能力：

```
Device State → Automation → Action
```

HomeState 扩展为：

```
Device Events → Context Engine → Semantic State → Virtual Sensors → HA Automation
```

### 解决的核心问题

| HA 现有限制                | HomeState 解决方案       |
| -------------------------- | ------------------------ |
| 设备状态是事实，没有语义   | 设备语义建模             |
| 自动化是规则，无法泛化     | 房间级上下文推理         |
| 多设备组合场景需要大量 YAML | 用户自定义语义解释       |
| DIY 设备语义无法统一表达   | 自动生成虚拟传感器       |

---

## 系统架构

### 总体分层

```
Home Assistant
    ↓ (WebSocket Event Bus)
HomeState Core Service (Go)
    ↓
Facts Layer        — 原始事件结构化记录
    ↓
Semantic Layer     — Entity → 人类语义映射
    ↓
Context Engine     — 家庭状态空间维护
    ↓
Guardrails Engine  — 硬规则边界（优先于 AI）
    ↓
Decision Layer     — 动作决策 + 虚拟状态输出
    ↓
HA Service Call / Virtual Sensors
```

### 各层职责

#### 1. Facts Layer（事实层）

接收 HA 原始事件，不做推理，只做结构化记录和时间序列维护。

数据来源：
- motion sensor / door sensor / light state
- power usage / presence (WiFi/BLE)
- pressure sensors / manual toggles

#### 2. Semantic Layer（语义层）

将 HA entity 转换为人类语义。示例：

```yaml
binary_sensor.desk_motion:
  room: study
  semantic: desk_presence
  meaning:
    - user_at_computer
    - working_indicator

light.study_main:
  role: main_light
  control_policy: auto

light.study_led:
  role: ambient_light
  control_policy: manual_protected
```

来源：用户自然语言配置 / AI 自动推断（可编辑）/ 用户修正反馈。

#### 3. Context Engine（上下文引擎）

维护当前家庭状态空间，增量更新（event-driven），不全量推理，可回溯历史。

输出示例：

```json
{
  "house_mode": "single_person",
  "rooms": {
    "study": { "occupancy": true, "confidence": 0.91 },
    "bedroom": { "occupancy": false, "confidence": 0.84 }
  },
  "activity": { "working": true, "sleeping": false },
  "current_room": "study"
}
```

#### 4. Guardrails Engine（规则边界）

硬规则系统，不依赖 AI，优先级高于 Context Engine。

```yaml
rules:
  - id: night_no_auto_light
    condition:
      after: "23:30"
      before: "07:00"
    effect:
      deny:
        - auto_turn_on_main_light

  - id: multi_room_disable_auto
    condition:
      active_rooms_gte: 2
    effect:
      set_mode: safe_mode

  - id: low_confidence_block
    condition:
      context_confidence_lt: 0.75
    effect:
      require_confirmation: true
```

#### 5. Decision Layer（决策层）

根据 Context + Guardrails 输出：是否执行、是否需确认、是否更新虚拟状态。

```json
{
  "action": "light.turn_off",
  "target": "light.bedroom_main",
  "allowed": true,
  "confidence": 0.87,
  "reason": "bedroom occupancy low confidence and user currently in study",
  "guardrails_passed": true
}
```

---

## Home Assistant 集成方式

### 集成形式

标准 HA Custom Component：`custom_components/homestate/`

### 核心能力

**1) WebSocket Event Listener**
订阅：state_changed / call_service / events / device_tracker

**2) Virtual Sensors 写回 HA**
```
sensor.homestate_current_room
binary_sensor.homestate_working
binary_sensor.homestate_sleeping
sensor.homestate_confidence
```

**3) Service Bridge**
```yaml
service: homestate.refresh_context
service: homestate.set_semantic
service: homestate.override_mode
```

---

## 数据模型

### Fact Event
```json
{ "entity_id": "binary_sensor.desk_motion", "state": "on", "timestamp": 0 }
```

### Semantic Mapping
```json
{ "entity_id": "binary_sensor.desk_motion", "room": "study", "semantic": "desk_presence", "confidence": 0.9 }
```

### Context State
```json
{ "study": { "occupancy": true, "confidence": 0.91 } }
```

### Decision Log
```json
{ "action": "turn_off", "entity": "light.bedroom_main", "reason": "bedroom empty inferred", "confidence": 0.87 }
```

---

## 运行模式

| 模式 | 行为 | 用途 |
|------|------|------|
| **Observe** | 只输出 Context，不执行动作 | 调试、语义建模 |
| **Suggest** | 输出建议，需用户确认 | 初步上线 |
| **Auto** | 满足 Guardrails 自动执行 | 成熟运行 |

---

## 核心设计原则

1. **不做身份识别** — 只做房间 occupancy 和行为状态，不追踪个人身份
2. **Context 是唯一真相层** — 所有自动化依赖 Context State，不依赖 raw sensor
3. **AI 只做三件事** — 语义映射、上下文推断、解释/建议；不强制执行、不绕过规则
4. **Virtual Sensor 优先** — HA 只看到虚拟传感器，不直接依赖 AI

---

## 技术选型

| 层      | 选型                              |
| ------- | --------------------------------- |
| Core    | Go 1.25，WebSocket client，轻量 HTTP server |
| Storage | SQLite（v0.1）→ Postgres（v0.2+） |
| AI      | OpenAI-compatible 接口（OpenAI / Claude / Gemini / Ollama / DeepSeek） |
| HA 集成 | Python custom component，HA State Machine + Service API |

---

## MVP 定义

### 目标场景

单人家庭：人来灯亮、人走灯灭、主灯自动控制、氛围灯不干扰。

### MVP 输出

- `sensor.homestate_current_room`
- `binary_sensor.homestate_room_occupancy`
- `binary_sensor.homestate_working` / `binary_sensor.homestate_sleeping`
- 灯控决策日志

### MVP 不做

多人身份识别 / 摄像头 / 全屋自动化接管 / 复杂学习系统

---

## 扩展路线

| 版本 | 内容 |
|------|------|
| v0.2 | 纠错学习、自动化建议引擎 |
| v0.3 | 多房间关联模型、时序行为模式 |
| v0.4 | 访客模式推断、异常检测 |
