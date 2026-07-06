# HomeState

Home Assistant 的语义上下文层 — 将传感器事件转化为家庭状态模型，以虚拟传感器形式回写 HA。

## 安装

### HACS 安装（推荐）

1. 打开 HA → **HACS** → **集成** → 右上角 **三点** → **自定义存储库**
2. 地址填 `https://github.com/myczh-1/HomeState`，类别选 **集成**
3. 点添加，在列表里找到 **HomeState** → 下载
4. **重启 HA**
5. **设置 → 设备与服务 → 添加集成** → 搜索 **HomeState**
6. 选择运行模式（建议先用 `observe`）
7. 在集成选项中添加你的传感器映射

### 配置语义映射

安装后进入 **设置 → 设备与服务 → HomeState → 选项**：

1. 选择运行模式
2. 点击 **添加传感器映射**
3. 填入：
   - **Entity ID**：你的传感器，如 `binary_sensor.study_motion`
   - **Room**：房间名，如 `study`
   - **语义类型**：`room_motion`（房间移动）/ `desk_presence`（桌前有人）/ `presence`（存在）/ `door`（门）
   - **置信度**：0.0–1.0，默认 0.95

## 运行模式

| 模式 | 行为 |
|------|------|
| `observe` | 只输出上下文，不执行动作（默认，适合调试） |
| `suggest` | 输出建议，需用户确认 |
| `auto` | 满足 Guardrails 自动执行 |

## 虚拟传感器

安装后 HA 中自动创建：

- `sensor.homestate_current_room` — 当前房间
- `sensor.homestate_house_mode` — 家庭模式（single_person / multi_person / empty）
- `binary_sensor.homestate_working` — 是否在工作
- `binary_sensor.homestate_sleeping` — 是否在睡觉
- `binary_sensor.homestate_<房间>_occupancy` — 每个房间的占用状态及置信度

## 设备状态 → 语义理解示例

```yaml
binary_sensor.study_motion:
  room: study
  semantic: room_motion
  # → 自动推断 study 房间有人

binary_sensor.desk_motion:
  room: study
  semantic: desk_presence
  # → 自动推断正在工作

binary_sensor.bedroom_motion:
  room: bedroom
  semantic: room_motion
  # → 自动推断 bedroom 房间有人
```

## Guardrails 硬规则

内置三条默认规则（不可被 AI 覆盖）：

1. **夜间禁止自动开灯**：23:30–07:00
2. **多房间模式禁用自动**：≥2 个房间有人时进入安全模式
3. **低置信度拦截**：任何房间置信度 < 0.75 时需要确认
