# HomeState

Home Assistant 的语义上下文层 — 将传感器事件转化为家庭状态模型，以虚拟传感器形式回写 HA。

## 安装

### 1. HomeState Core（Go 服务）

**Docker 方式**（推荐）：

```bash
git clone https://github.com/huanghe/HomeState.git
cd HomeState
cp data/config.json.example data/config.json
# 编辑 data/config.json，填入你的 HA 地址和 token
docker compose up -d
```

**直接运行**：

```bash
go build -o homestate ./cmd/homestate/
cp config.example.json config.json
# 编辑 config.json
./homestate -config config.json
```

### 2. HomeState HA 集成

**HACS 安装**（推荐）：

1. HA → HACS → 集成 → 右上角三点 → 自定义存储库
2. 输入 `https://github.com/huanghe/HomeState`，类别选"集成"
3. 点击安装
4. 重启 HA
5. 设置 → 设备与服务 → 添加集成 → 搜索 "HomeState"
6. 填入 Go 服务地址（如 `http://你的IP:8099`）

### 3. 配置语义映射

编辑 Go 服务目录下的 `semantics.json`（或 `data/semantics.json`），将你的传感器映射到房间和语义：

```json
[
  {
    "entity_id": "binary_sensor.你的运动传感器",
    "room": "study",
    "semantic": "room_motion",
    "confidence": 0.85
  }
]
```

## 运行模式

| 模式 | 行为 |
|------|------|
| `observe` | 只输出上下文，不执行动作（默认，适合调试） |
| `suggest` | 输出建议，需用户确认 |
| `auto` | 满足 Guardrails 自动执行 |

## 虚拟传感器

安装后 HA 中会出现：

- `sensor.homestate_current_room` — 当前房间
- `sensor.homestate_house_mode` — 家庭模式
- `binary_sensor.homestate_working` — 是否在工作
- `binary_sensor.homestate_sleeping` — 是否在睡觉
- `binary_sensor.homestate_<房间>_occupancy` — 每个房间的占用状态

## API

Go 服务提供 HTTP API：

```
GET  /api/context    — 当前上下文状态
GET  /api/semantic   — 所有语义映射
POST /api/semantic/set — 设置语义映射
GET  /api/mode       — 当前运行模式
GET  /api/health     — 健康检查
```
