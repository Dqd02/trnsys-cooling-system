# S2 低碳窗口目标下水蓄冷控制信号 Equation 指导

## 1. 审查立场与控制取舍

本指导面向 `S2/Project11.dck` 的集中供冷水蓄冷系统。系统包含 1 台蓄冷冷机（Unit 35）、2 台基载冷机（Unit 9/12）、水蓄冷罐（Unit 7）、释冷水泵（Unit 6）、蓄冷水泵（Unit 32）、三档用户侧回水泵（Unit 40 小泵、Unit 43 大泵、Unit 33 水箱泵）、Unit 42 三入口混合器、Unit 14/29 分流阀以及冷却塔/冷却水泵。

**核心取舍：**

1. 低碳窗口策略的目标不是固定 0-8 点蓄冷，而是在工作日低碳排放时段尽量用低碳电力蓄冷。
2. 当处于低碳窗口且有负荷时，负荷由基载冷机直接供冷，水箱仍按 SOC 判断是否蓄冷；这样避免一边低碳蓄冷、一边又从水箱释冷的逻辑冲突。
3. 当不处于低碳窗口且有负荷时，优先使用水箱释冷；只有水箱冷量不足时才切换到基载冷机直供。
4. 冷机 1/2 开启台数阈值采用 **1500 kW**，不是 1550 kW。

## 2. S2 模型关键核查

### 2.1 负荷与低碳窗口信号

`load_year_15min_new.csv` 由 Unit 22 读入，当前负荷数值量级为 `10^6 kJ/h`，因此台数判断应折算为 kW：

```trnsys
LoadKW = [22,1]/3600 ! Unit 22 原始负荷按 kJ/h 处理，除以 3600 后得到 kW
```

低碳窗口信号按你的说明记为 `CO2_window`：

- `CO2_window = 1`：该 15 min 时刻为每日碳因子最低 25% 的低碳窗口。
- `CO2_window = 0`：非低碳窗口。
- 低碳窗口来自 `analysis_report.md` 中的每日 P25 标记逻辑，并经过孤立点连续性修正。

**重要审查意见：** 当前 `S2/Project11.dck` 中 Unit 50/51/52 名称为“碳窗口”，但外部文件仍 `ASSIGN "load_year_15min_new.csv"`。这不像真正的低碳窗口 0/1 标记文件。若 Equation 中实际使用 `[50,1]` 作为 `CO2_window`，必须先确认 Unit 50 读取的是低碳窗口标记文件，而不是负荷文件。

### 2.2 Type534 水箱输出

当前 Unit 7 为 Type534，2 个 Port、25 个节点。按输出编号：

- `[7,1]` = Port-1 出口温度，释冷侧送往 Unit 6。
- `[7,2]` = Port-1 出口流量。
- `[7,3]` = Port-2 出口温度，蓄冷侧送往 Unit 35。
- `[7,4]` = Port-2 出口流量。
- `[7,5]` = 水箱平均温度。
- `[7,18]` = 节点 1 温度。
- `[7,30]` = 节点 13 温度。
- `[7,42]` = 节点 25 温度。

### 2.3 Type24 与分流阀出口方向

S2 中 Unit 41/46 的 Type24 是积分器，用于能耗/碳排积分，不是分流阀。你给出的公式实际对应 Type11 mode=2 这类受控分流逻辑：

```trnsys
flow2 = flow*gam
flow1 = flow*(1-gam)
Output1 = tin
Output2 = flow1
Output3 = tin
Output4 = flow2
```

因此对分流阀应按以下方向理解：

- `outlet1` 对应 `flow1 = flow*(1-gam)`。
- `outlet2` 对应 `flow2 = flow*gam`。
- `gam=0`：全部走 outlet1。
- `gam=1`：全部走 outlet2。
- `gam=0.5`：两路平分。

在当前系统中：

- Unit 14 分流阀-2：outlet1 到冷机1，outlet2 到冷机2。单冷机时 `gam=0`，双冷机时 `gam=0.5`。
- Unit 29 分流阀-3：outlet1 到蓄冷罐 Port-1，outlet2 到管道-4/冷机侧。水箱释冷时 `gam=0`，冷机直供时 `gam=1`。

## 3. 推荐 Equation 公式

以下公式用于替换 S2 当前 `状态判断-3` 中的传统 0-8 点蓄冷逻辑。若 `CO2_window` 已作为 Equation 输入变量接入，可直接使用；若由 Unit 50 输出接入，可先写：

```trnsys
CO2_window = [50,1] ! 示例：若 Unit 50 output1 是低碳窗口 0/1 标记，则用该输出作为低碳窗口信号
```

### 3.1 水箱状态与负荷判断

```trnsys
T_cold_sp = 4 ! 蓄冷目标供水温度，代表水箱冷端接近满蓄冷时的温度
T_warm_ref = 12 ! 回水暖态参考温度，代表水箱基本放空时的温度基准
dT_dead = 1 ! 温度死区，避免节点温度微小波动导致设备频繁启停

LoadRaw = [22,1] ! Unit 22 读取的负荷原始值，当前应按 kJ/h 理解
LoadKW = LoadRaw/3600 ! 将负荷折算为 kW，用于 1500 kW 冷机台数判据
HasLoad = gt(LoadKW,5) ! 有效负荷判断，5 kW 以下视为无制冷需求或数值噪声

T_tank_avg = [7,5] ! Type534 水箱平均温度，用于估算整体 SOC
T_node_top = [7,18] ! 水箱节点 1 温度，用于判断冷端是否接近蓄满
T_node_mid = [7,30] ! 水箱节点 13 温度，用于判断温跃层是否推进到中部
T_node_bot = [7,42] ! 水箱节点 25 温度，用于判断暖端是否接近回水温度

SOC = max(0,min(1,(T_warm_ref-T_tank_avg)/(T_warm_ref-T_cold_sp))) ! 水箱蓄冷状态，0=空/暖，1=满/冷
TankFull = lt(T_node_top,T_cold_sp+dT_dead)*lt(T_node_mid,T_cold_sp+1.5) ! 顶部与中部均接近冷水温度，判定水箱基本蓄满
TankEmpty = gt(T_node_bot,T_warm_ref-dT_dead)*gt(T_node_mid,T_warm_ref-3) ! 底部与中部均偏暖，判定水箱可用冷量不足

SOC_Recharge = 0.92 ! 低碳窗口内，满罐后若 SOC 因散热/混合降到 0.92 以下，则允许补冷
SOC_DischargeMin = 0.10 ! SOC 低于 10% 时禁止继续优先释冷，避免供水温度失控

Chg_bySOC = lt(SOC,SOC_Recharge)*(1-TankFull) ! 只有未满且 SOC 低于补冷阈值时才允许蓄冷
Dch_bySOC = gt(SOC,SOC_DischargeMin)*(1-TankEmpty) ! 只有 SOC 足够且水箱未空时才允许释冷
```

### 3.2 工作日、负荷时段与低碳窗口判断

```trnsys
HourOfDay = time-24*int(time/24) ! 当前时刻在一天内的小时数
DayNum = int(time/24) ! 从仿真起点计算的日序号
WeekIndex0 = DayNum-7*int(DayNum/7) ! 周内索引，0-6 循环
WeekdayOffset = 0 ! 周几偏移量，应按负荷文件首日校准
RawWeekIndex = WeekIndex0+WeekdayOffset ! 加偏移后的周索引
Weekday = RawWeekIndex-7*int(RawWeekIndex/7) ! 0=周一，1=周二，...，6=周日

IsWorkday = lt(Weekday,5) ! 工作日信号，周一至周五为 1，周末为 0
IsLoadTime = ge(HourOfDay,8)*lt(HourOfDay,22) ! 工作日 8:00-22:00 为负荷可出现时段
LoadWindow = IsWorkday*IsLoadTime*HasLoad ! 只有工作日 8-22 点且有负荷时才需要供冷

CO2_window01 = max(0,min(1,CO2_window)) ! 将低碳窗口信号限幅到 0-1，防止读入异常值
IsLowCarbon = gt(CO2_window01,0.5) ! 将低碳窗口转成布尔信号，1=低碳，0=非低碳
CarbonChargeWindow = IsWorkday*IsLowCarbon ! 仅工作日低碳窗口允许蓄冷；不再限制 0-8 点
```

### 3.3 模式判定

```trnsys
ChargeMode = CarbonChargeWindow*Chg_bySOC ! 工作日低碳窗口且水箱未满时，开启蓄冷

TankMode = LoadWindow*(1-CarbonChargeWindow)*Dch_bySOC ! 非低碳窗口、有负荷且水箱有冷量时，优先水箱释冷

DirectChillerMode = min(1,LoadWindow*(CarbonChargeWindow+(1-CarbonChargeWindow)*(1-Dch_bySOC))) ! 有负荷时：低碳窗口直接由冷机供冷；非低碳窗口仅在水箱不可用时由冷机供冷，并限幅到 0-1

HighLoad = ge(LoadKW,1500) ! 冷机台数阈值，LoadKW >= 1500 kW 开两台，低于 1500 kW 开一台
OneChillerMode = DirectChillerMode*(1-HighLoad) ! 冷机直供且负荷低于 1500 kW，只开冷机1
TwoChillerMode = DirectChillerMode*HighLoad ! 冷机直供且负荷达到 1500 kW，冷机1和冷机2同时开启
```

这组模式的含义是：

- 低碳窗口、有负荷：水箱不释冷，冷机1/2按负荷阈值直接供冷；若水箱未满，同时蓄冷机3给水箱蓄冷。
- 低碳窗口、无负荷：若水箱未满，只蓄冷；若水箱已满，全部设备停。
- 非低碳窗口、有负荷、水箱有冷量：优先水箱释冷，冷机1/2关闭。
- 非低碳窗口、有负荷、水箱冷量不足：基载冷机直供，按 1500 kW 判断开一台或两台。
- 非低碳窗口、无负荷：不蓄冷、不释冷、不启基载冷机。

## 4. 设备控制信号

### 4.1 蓄冷冷机及冷却侧

```trnsys
Chiller3_ON = ChargeMode ! Unit 35 蓄冷机3：只在低碳窗口且水箱需要补冷时开启
Pump32_ON = ChargeMode ! Unit 32 蓄冷水泵：与蓄冷机3同步，形成 蓄冷机3 -> 蓄冷泵 -> 水箱 Port-2
Tower3_ON = ChargeMode ! Unit 36 冷却塔3：与蓄冷机3同步
CWPump3_ON = ChargeMode ! Unit 38 冷却水泵3：与蓄冷机3同步
```

### 4.2 水箱释冷与三档回水泵

```trnsys
Pump6_ON = TankMode ! Unit 6 释冷水泵：仅水箱释冷模式开启
Pump33_ON = TankMode ! Unit 33 水箱泵：水箱释冷回水泵，额定流量 322200 kg/h
Pump40_ON = OneChillerMode ! Unit 40 小泵：单冷机直供回水泵，额定流量 150300 kg/h
Pump43_ON = TwoChillerMode ! Unit 43 大泵：双冷机直供回水泵，额定流量 300600 kg/h
```

回水总管后泵选择：

| 模式 | 回水总管后应走的泵 | 下游路径 |
|---|---|---|
| 水箱释冷 | Unit 33 水箱泵 | Unit 42 混合器 -> Unit 29 outlet1 -> 蓄冷罐 Port-1 |
| 单冷机直供 | Unit 40 小泵 | Unit 42 混合器 -> Unit 29 outlet2 -> 管道-4 -> Unit 14 outlet1 -> 冷机1 |
| 双冷机直供 | Unit 43 大泵 | Unit 42 混合器 -> Unit 29 outlet2 -> 管道-4 -> Unit 14 两路平分 -> 冷机1/2 |

三台回水泵必须互斥开启。若 Unit 42 三个入口同时出现两个以上非零流量，说明控制信号或接线存在错误。

### 4.3 基载冷机、冷冻水泵、冷却塔和冷却水泵

```trnsys
Chiller1_ON = min(1,OneChillerMode+TwoChillerMode) ! Unit 9 冷机1：所有冷机直供模式均开启
Chiller2_ON = TwoChillerMode ! Unit 12 冷机2：仅 LoadKW >= 1500 kW 的双冷机直供模式开启

Pump10_ON = Chiller1_ON ! Unit 10 供冷水泵-1：与冷机1同步
Pump13_ON = Chiller2_ON ! Unit 13 供冷水泵-2：与冷机2同步

Tower1_ON = Chiller1_ON ! Unit 18 冷却塔1：与冷机1同步
CWPump1_ON = Chiller1_ON ! Unit 19 冷却水泵1：与冷机1同步
Tower2_ON = Chiller2_ON ! Unit 21 冷却塔2：与冷机2同步
CWPump2_ON = Chiller2_ON ! Unit 20 冷却水泵2：与冷机2同步
```

### 4.4 分流阀

```trnsys
Div14_gam = 0.5*TwoChillerMode ! Unit 14：单冷机时 gam=0 全进冷机1；双冷机时 gam=0.5 平分到冷机1/2
Div29_gam = DirectChillerMode ! Unit 29：水箱释冷时 gam=0 回水进水箱；冷机直供时 gam=1 全进管道-4
```

注意：低碳窗口内即使水箱已满、`ChargeMode=0`，只要仍有负荷且 `CarbonChargeWindow=1`，`DirectChillerMode` 仍应为 1，负荷由基载冷机直接承担，不应改走水箱释冷。

## 5. 建议接线表

| 设备 | 控制输入 | 建议信号 |
|---|---|---|
| Unit 6 释冷水泵 | Control signal | `Pump6_ON` |
| Unit 9 冷机1 | Chiller Control Signal | `Chiller1_ON` |
| Unit 10 供冷水泵-1 | Control signal | `Pump10_ON` |
| Unit 12 冷机2 | Chiller Control Signal | `Chiller2_ON` |
| Unit 13 供冷水泵-2 | Control signal | `Pump13_ON` |
| Unit 14 分流阀-2 | Control signal | `Div14_gam` |
| Unit 18 冷却塔1 | Fan Control Signal | `Tower1_ON` |
| Unit 19 冷却水泵1 | Control signal | `CWPump1_ON` |
| Unit 20 冷却水泵2 | Control signal | `CWPump2_ON` |
| Unit 21 冷却塔2 | Fan Control Signal | `Tower2_ON` |
| Unit 29 分流阀-3 | Control signal | `Div29_gam` |
| Unit 32 蓄冷水泵 | Control signal | `Pump32_ON` |
| Unit 33 水箱泵 | Control signal | `Pump33_ON` |
| Unit 35 蓄冷机3 | Chiller Control Signal | `Chiller3_ON` |
| Unit 36 冷却塔3 | Fan Control Signal | `Tower3_ON` |
| Unit 38 冷却水泵3 | Control signal | `CWPump3_ON` |
| Unit 40 小泵 | Control signal | `Pump40_ON` |
| Unit 43 大泵 | Control signal | `Pump43_ON` |

## 6. 宏观策略自检

1. 工作日低碳窗口、无负荷、水箱未满：只开蓄冷机3、蓄冷泵、冷却塔3、冷却水泵3。
2. 工作日低碳窗口、有负荷、水箱未满：蓄冷机3给水箱蓄冷；基载冷机1/2按 1500 kW 阈值直接供负荷。
3. 工作日低碳窗口、有负荷、水箱已满：蓄冷机3停止；基载冷机1/2仍按负荷直接供冷，不使用水箱释冷。
4. 工作日非低碳窗口、有负荷、水箱有冷量：优先水箱释冷，冷机1/2及其冷却侧全部关闭。
5. 工作日非低碳窗口、有负荷、水箱冷量不足：基载冷机直供，`LoadKW < 1500` 开冷机1，`LoadKW >= 1500` 开冷机1/2。
6. 工作日无负荷但处于低碳窗口时：只允许蓄冷补冷，不开启冷机1/2、供冷水泵、释冷泵和用户侧回水泵。
7. 周末：`IsWorkday=0`，本策略不蓄冷、不释冷、不启基载冷机。
8. Unit 29 分流方向必须正确：水箱释冷 `gam=0` 走 outlet1 回水箱；冷机直供 `gam=1` 走 outlet2 到管道-4。

## 7. 仍需核实的问题

1. **低碳窗口读入文件**：S2 当前 Unit 50/51/52 外部文件看起来仍是 `load_year_15min_new.csv`。必须改为真正的 0/1 低碳窗口标记文件，或确认 `CO2_window` 已由其他方式正确输入。
2. **周几偏移量**：`WeekdayOffset=0` 只是占位，应根据负荷文件第一天对应的真实星期校准，否则工作日/周末判断会错位。
3. **1500 kW 阈值**：单台基载冷机额定约 1400 kW，若以 1500 kW 作为单/双冷机切换点，应在论文中说明该阈值来自工程调度死区或机组允许工况。
4. **低碳窗口与电价窗口不同**：该策略将高低碳作为唯一蓄冷依据，不保证电费最优；若论文比较“低碳优先”和“传统谷电优先”，应分别统计能耗、碳排和运行费用。

## 8. 自评分与可落地建议

**自评分：91/100。**

评分理由：控制逻辑已覆盖低碳蓄冷、有负荷直供、非低碳优先释冷、水箱耗尽切冷机、三档泵互斥、Type11/Type24 出口方向等关键问题。扣分主要因为没有实际运行 TRNSYS 验证设备启停序列，且低碳窗口文件在当前 DCK 中疑似尚未正确接入。

三点可落地改进：

1. 将 `CO2_window`、`CarbonChargeWindow`、`ChargeMode`、`TankMode`、`DirectChillerMode`、`Pump33_ON`、`Pump40_ON`、`Pump43_ON` 输出到 Type65/Printer，抽查至少 3 个工作日和 1 个周末。
2. 先修正并验证低碳窗口数据源：确保 `CO2_window` 是 0/1 标记，而不是负荷或原始碳因子；建议用 24 h 序列图核对每天约 25% 时段为 1。
3. 做敏感性对比：分别采用 P25、P40、P60 低碳窗口，比较总碳排、蓄冷机启停次数、日间供水温度和水箱 SOC 轨迹，判断 P25 是否过于严格。
