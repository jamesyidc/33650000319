# 📊 ABC Position 信号标记功能说明

## 功能概述

在ABC Position页面的图表中，系统会自动计算并标记两种重要信号：
1. **4小时最高点** - 金色星星标记 ⭐
2. **平仓信号** - 红色旗帜标记 🚩

## 信号算法

### 1. 4小时最高点（⭐金色菱形）

**定义**：在4小时（240分钟）滚动窗口内，盈亏百分比(pnl_pct)达到最高值的时刻。

**计算逻辑**：
```
对于每个时间点 i：
  1. 定义窗口：从 (i-240分钟) 到 i
  2. 在窗口内找到最大的 pnl_pct
  3. 如果当前点是窗口内最大值且 pnl > 0
     → 标记为"4小时最高点"
```

**标记条件**：
- ✅ 在4小时窗口内是最高盈利点
- ✅ 盈利百分比 > 0（只标记盈利状态）
- ✅ 避免重复标记同一个点

**图表显示**：
- 符号：⭐（金色菱形 diamond）
- 大小：16px
- 标签："⭐4H高"
- 颜色：金黄色 (#fbbf24)

---

### 2. 平仓信号（🚩红色旗帜）

**定义**：4小时最高点出现后，如果在接下来的2.5小时（150分钟）内没有出现更高的盈利点，则触发平仓信号。

**计算逻辑**：
```
对于每个4小时最高点 hp：
  1. 记录最高点的 pnl_pct
  2. 从最高点往后看 2.5小时（150分钟）
  3. 检查这段时间内是否有 pnl_pct > hp.pnl
  4. 如果没有创新高
     → 在 hp + 2.5小时的位置标记"平仓信号"
```

**标记条件**：
- ✅ 基于已确认的4小时最高点
- ✅ 后续2.5小时内没有突破该高点
- ✅ 标记位置：最高点 + 2.5小时

**图表显示**：
- 符号：🚩（红色图钉 pin）
- 大小：18px
- 标签："🚩平仓"
- 颜色：红色 (#ef4444)

---

## 数据存储格式

### JSONL文件位置
```
/home/user/webapp/data/abc_position_signals/signals_YYYYMMDD.jsonl
```

### 文件命名规则
- 按日期分文件：`signals_20260319.jsonl`
- 每天一个文件
- 使用北京时间日期

### 数据格式

#### 最高点记录
```jsonl
{
  "account": "A",
  "type": "high_point",
  "timestamp": "2026-03-19T10:30:00+08:00",
  "pnl": 5.67,
  "idx": 450,
  "created_at": "2026-03-19T15:00:00+08:00"
}
```

#### 平仓信号记录
```jsonl
{
  "account": "B",
  "type": "close_signal",
  "timestamp": "2026-03-19T13:00:00+08:00",
  "pnl": 4.23,
  "idx": 600,
  "high_point_idx": 450,
  "high_point_pnl": 5.67,
  "created_at": "2026-03-19T15:00:00+08:00"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| account | string | 账户ID（A/B/C/D） |
| type | string | 信号类型（high_point / close_signal） |
| timestamp | string | 信号触发时间（北京时间，ISO格式） |
| pnl | number | 盈亏百分比 |
| idx | integer | 数据点索引（在historyData数组中的位置） |
| high_point_idx | integer | 关联的最高点索引（仅平仓信号） |
| high_point_pnl | number | 关联的最高点盈利（仅平仓信号） |
| created_at | string | 信号计算时间（记录创建时间） |

---

## API接口

### 1. 获取信号数据

**接口**：`GET /abc-position/api/signals`

**参数**：
- `date` (可选): 日期，格式 YYYYMMDD，默认今天（北京时间）
- `account` (可选): 账户ID（A/B/C/D），默认 'all' 返回所有账户

**示例请求**：
```bash
# 获取今天所有账户的信号
curl http://localhost:9002/abc-position/api/signals

# 获取指定日期的信号
curl http://localhost:9002/abc-position/api/signals?date=20260319

# 获取特定账户的信号
curl http://localhost:9002/abc-position/api/signals?date=20260319&account=A
```

**响应格式**：
```json
{
  "success": true,
  "data": [
    {
      "account": "A",
      "type": "high_point",
      "timestamp": "2026-03-19T10:30:00+08:00",
      "pnl": 5.67,
      "idx": 450
    },
    {
      "account": "A",
      "type": "close_signal",
      "timestamp": "2026-03-19T13:00:00+08:00",
      "pnl": 4.23,
      "idx": 600,
      "high_point_idx": 450,
      "high_point_pnl": 5.67
    }
  ],
  "date": "20260319"
}
```

---

### 2. 保存信号数据

**接口**：`POST /abc-position/api/signals`

**参数**：
- `date` (可选): 日期，格式 YYYYMMDD，默认今天

**请求体**：
```json
{
  "signals": [
    {
      "account": "A",
      "type": "high_point",
      "timestamp": "2026-03-19T10:30:00+08:00",
      "pnl": 5.67,
      "idx": 450
    }
  ]
}
```

**响应格式**：
```json
{
  "success": true,
  "message": "已保存2个信号",
  "date": "20260319"
}
```

---

## 前端函数说明

### calculateSignals(historyData, account)

计算指定账户的所有信号。

**参数**：
- `historyData` - 历史数据数组
- `account` - 账户ID（A/B/C/D）

**返回**：
```javascript
{
  highPoints: [
    { idx, timestamp, pnl, type: 'high_point' },
    ...
  ],
  closeSignals: [
    { idx, timestamp, pnl, highPointIdx, highPointPnl, type: 'close_signal' },
    ...
  ]
}
```

---

### saveSignals(date, account, signals)

保存信号到后端JSONL文件。

**参数**：
- `date` - 日期字符串（YYYYMMDD）
- `account` - 账户ID
- `signals` - calculateSignals返回的信号对象

**示例**：
```javascript
const signals = calculateSignals(historyData, 'A');
await saveSignals('20260319', 'A', signals);
```

---

### loadSignals(date, account)

从后端加载信号数据。

**参数**：
- `date` - 日期字符串（YYYYMMDD）
- `account` - 账户ID或'all'

**返回**：
```javascript
[
  { account, type, timestamp, pnl, idx, ... },
  ...
]
```

---

## 图表标记说明

### 标记优先级（从上到下）

1. 🟣 **加仓点（紫色圆圈）**
   - 位置：position_count增加的时刻
   - 标签："+N仓"

2. ⭐ **4小时最高点（金色菱形）**
   - 位置：4小时窗口内的最高盈利点
   - 标签："⭐4H高"

3. 🚩 **平仓信号（红色旗帜）**
   - 位置：最高点后2.5小时无新高的时刻
   - 标签："🚩平仓"

---

## 使用场景

### 1. 实时监控

当页面自动刷新时（每60秒），系统会：
1. 加载最新的历史数据
2. 计算所有账户的信号
3. 自动保存到JSONL文件
4. 在图表上显示标记

### 2. 历史回顾

选择历史日期时：
1. 加载该日期的历史数据
2. 重新计算信号（如果尚未计算）
3. 显示该日的所有标记

### 3. 交易决策辅助

- **看到⭐最高点**：表示当前是4小时内最佳盈利点，可以考虑部分获利
- **看到🚩平仓信号**：表示盈利已经停滞2.5小时，建议平仓

---

## 技术细节

### 时间窗口说明

```
4小时窗口 = 240分钟 = 240个数据点（每分钟1个）
2.5小时窗口 = 150分钟 = 150个数据点
```

### 性能优化

- 信号计算在前端进行，避免重复计算
- 结果保存到JSONL文件，方便查询和分析
- 按账户分别计算和保存

### 数据一致性

- 每次加载图表数据时重新计算信号
- 确保标记与当前数据完全匹配
- 使用北京时间统一时区

---

## 常见问题

### Q: 为什么有些最高点没有平仓信号？

A: 可能的原因：
1. 最高点是当天最后的数据，后续没有2.5小时的数据
2. 最高点后2.5小时内又出现了更高的盈利点

### Q: 信号会不会重复标记？

A: 不会。计算逻辑中有去重检查，确保每个点只标记一次。

### Q: 如何查看历史信号数据？

A: 有两种方式：
1. 前端：选择历史日期，图表会自动显示
2. 后端：直接查看 JSONL 文件
```bash
cat data/abc_position_signals/signals_20260319.jsonl
```

---

## 示例场景

### 场景1：顺利获利

```
10:00  +3%  ← 加仓
11:00  +5%  ← ⭐ 4小时最高点
11:30  +4%
12:00  +3.5%
13:30  +3%  ← 🚩 平仓信号（2.5小时无新高）
```

**解读**：在11:00达到5%的高点后，接下来2.5小时内没有突破，系统在13:30发出平仓信号。

---

### 场景2：继续上涨

```
10:00  +3%  ← 加仓
11:00  +5%  ← ⭐ 4小时最高点
12:00  +4%
13:00  +6%  ← ⭐ 新的4小时最高点（前一个信号失效）
```

**解读**：虽然11:00是当时的最高点，但13:00出现了更高的6%，所以不会产生平仓信号。

---

## 文件清单

### 后端代码
- `core_code/app.py` - 信号API接口
  - `/abc-position/api/signals` (GET/POST)

### 前端代码
- `templates/abc_position.html`
  - `calculateSignals()` - 计算信号
  - `saveSignals()` - 保存信号
  - `loadSignals()` - 加载信号
  - `updateChart()` - 显示标记

### 数据目录
- `data/abc_position_signals/` - 信号数据存储

---

**更新时间**：2026-03-19  
**版本**：v1.2  
**状态**：✅ 已部署并测试
