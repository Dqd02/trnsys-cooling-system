# 传统集中供冷水蓄冷系统控制信号 Equation 指导

## 1. 审查立场与主要取舍

本指导面向 `full_storage/Project11.dck` 中的水蓄冷集中供冷系统。该系统由 1 台蓄冷冷机（Unit 35，约 3000 kW）、2 台基载冷机（Unit 9/12，2 x 1400 kW）、水蓄冷罐（Unit 7）、释冷泵（Unit 6）、蓄冷泵（Unit 32）、用户侧三档回水泵（Unit 40 小泵、Unit 43 大泵、Unit 33 水箱泵）及相应冷却塔和冷却水泵构成。

**控制取舍：**

1. 本文优先采用 TRNSYS `EQUATIONS` 可实现的最小逻辑，不引入额外优化调度或预测控制，便于直接接入现有模型。
2. 蓄冷“满停、冷量下降后补冷”用 SOC 与节点温度阈值近似实现。若要严格避免短周期启停，应后续增加 Type2 滞回控制器或显式状态保持单元。
3. 冷机台数切换按用户要求采用 **1500 kW**，不再使用 1550 kW。用户侧泵已改为三档：小泵 150300 kg/h、大泵 300600 kg/h、水箱泵 322200 kg/h，可分别精确匹配单冷机、双冷机和水箱释冷工况。

## 2. 现有模型关键连接核查

### 2.1 负荷数据量纲

`load_year_15min_new.csv` 由 Unit 22 读入，`Project11.dck` 中 Unit 4 `Type682` 直接使用 `[22,1]` 作为负荷输入。文件跳过 12865 行后出现约 `4.46E6 ~ 4.83E6` 的数值，按 TRNSYS 水侧负荷常用量纲应理解为 **kJ/h**，折算为约 `1239 ~ 1343 kW`。

因此，台数判断必须使用：

```trnsys
LoadKW = [22,1]/3600  ! 将 Type9 读取的 kJ/h 负荷折算为 kW；1500 kW 判据必须用折算后的值
```

不能直接用 `[22,1]` 与 1500 比较，否则阈值会错 3600 倍。

### 2.2 Type534 水箱输出编号

当前 Unit 7 为 Type534，2 个 Port、25 个节点。按 Type534 输出规则：

- `[7,1]` = Port-1 出口温度
- `[7,2]` = Port-1 出口流量
- `[7,3]` = Port-2 出口温度
- `[7,4]` = Port-2 出口流量
- `[7,5]` = 水箱平均温度
- `[7,18]` = 节点 1 温度
- `[7,30]` = 节点 13 温度
- `[7,42]` = 节点 25 温度

当前连接关系为：

- Port-1：用户释冷侧。`分流阀-3 outlet1 -> 水箱 Port-1 inlet`，`水箱 Outlet-1 -> 释冷水泵 Unit 6`。
- Port-2：夜间蓄冷侧。`水箱 Outlet-2 -> 蓄冷机3 Unit 35`，`蓄冷机3 -> 蓄冷水泵 Unit 32 -> 水箱 Port-2 inlet`。

因此，日间释冷应开启 Unit 6；夜间蓄冷应开启 Unit 35 与 Unit 32。

### 2.3 Type11/Type24 出口方向

当前 `Project11.dck` 实际使用的是 Type11f 分流阀，不是 Type24。Type11 mode=2 的分流规律为：

```trnsys
flow2 = flow*gam
flow1 = flow*(1-gam)
Output1 = tin
Output2 = flow1
Output3 = tin
Output4 = flow2
```

若后续改用或参照你给出的 Type24 逻辑，也应按同样方向理解：

- `outlet1` 对应 `flow1 = flow*(1-gam)`
- `outlet2` 对应 `flow2 = flow*gam`
- `gam=0`：全流量走 outlet1
- `gam=1`：全流量走 outlet2
- `gam=0.5`：两出口平分

现有关键分流阀应这样接：

- Unit 14 `分流阀-2`：outlet1 到冷机1，outlet2 到冷机2。单冷机运行时 `gam=0`；双冷机运行时 `gam=0.5`。
- Unit 29 `分流阀-3`：outlet1 到蓄冷罐 Port-1，outlet2 到管道-4/冷机侧。水箱释冷时 `gam=0`；冷机直供时 `gam=1`。

## 3. 推荐 Equation 控制公式

以下公式建议替换或扩展当前 `EQUATIONS "水箱状态判断"`。变量名保持工程含义清晰，便于后续把信号接到对应设备输入端。

```trnsys
T_cold_sp = 4        ! 供冷/蓄冷目标冷水温度，当前模型冷机 CHW Set Point 初值也是 4 C
T_warm_ref = 12      ! 回水暖态参考温度，用于定义水箱完全放空时的温度基准
dT_dead = 1          ! 节点温度判断死区，避免单个时间步温度波动造成频繁启停

LoadRaw = [22,1]     ! Unit 22 读取的负荷原始值；当前文件应按 kJ/h 处理
LoadKW = LoadRaw/3600 ! 将 kJ/h 折算为 kW，冷机台数 1500 kW 判据使用该变量
HasLoad = gt(LoadKW,5) ! 有效制冷需求判断；5 kW 作为数值噪声过滤阈值，防止零负荷时误开泵

T_tank_avg = [7,5]   ! Type534 输出 5 为水箱平均温度，用于估算整体蓄冷状态
T_node_top = [7,18]  ! Type534 节点 1 温度；当前模型以该节点代表水箱冷端/顶部状态
T_node_mid = [7,30]  ! Type534 节点 13 温度；用于判断温跃层是否推进到中部
T_node_bot = [7,42]  ! Type534 节点 25 温度；用于判断水箱暖端/底部是否已接近回水温度

SOC = max(0,min(1,(T_warm_ref-T_tank_avg)/(T_warm_ref-T_cold_sp))) ! 水箱蓄冷状态，0=接近 12 C 空罐，1=接近 4 C 满罐
TankFull = lt(T_node_top,T_cold_sp+dT_dead)*lt(T_node_mid,T_cold_sp+1.5) ! 顶部与中部都接近 4 C，说明可用冷量已基本蓄满
TankEmpty = gt(T_node_bot,T_warm_ref-dT_dead)*gt(T_node_mid,T_warm_ref-3) ! 底部与中部均偏暖，说明温跃层已耗尽，不能继续优先释冷

SOC_Recharge = 0.92  ! 满罐停止后，若散热或混合使 SOC 低于 0.92，则允许在蓄冷窗口内补冷
SOC_DischargeMin = 0.10 ! 低于 10% SOC 时认为水箱冷量不足，应切换到冷机直供，避免供水温度失控

Chg_bySOC = lt(SOC,SOC_Recharge)*(1-TankFull) ! 未满且 SOC 低于补冷阈值时允许蓄冷；满罐后自动停止
Dch_bySOC = gt(SOC,SOC_DischargeMin)*(1-TankEmpty) ! SOC 足够且水箱未空时允许释冷；水箱空后禁止继续优先释冷
```

```trnsys
HourOfDay = time-24*int(time/24) ! 当前仿真时刻在一天内的小时数，范围约 0-24
DayNum = int(time/24)            ! 从 TRNSYS 绝对仿真时间计算的日序号
WeekIndex0 = DayNum-7*int(DayNum/7) ! 周内索引，0-6 循环
WeekdayOffset = 0                ! 周几偏移量；必须按负荷文件首日校准，0 表示不偏移
RawWeekIndex = WeekIndex0+WeekdayOffset ! 加偏移后的周内索引
Weekday = RawWeekIndex-7*int(RawWeekIndex/7) ! 0=周一，1=周二，...，6=周日

IsWorkday = lt(Weekday,5)        ! 工作日为 1，周六周日为 0
IsChargeTime = lt(HourOfDay,8)   ! 0:00-8:00 为夜间蓄冷窗口
IsLoadTime = ge(HourOfDay,8)*lt(HourOfDay,22) ! 8:00-22:00 为工作日供冷窗口

ChargeWindow = IsWorkday*IsChargeTime ! 仅工作日夜间允许蓄冷；周末不蓄冷
LoadWindow = IsWorkday*IsLoadTime*HasLoad ! 仅工作日 8:00-22:00 且负荷大于噪声阈值时供冷
```

```trnsys
ChargeMode = ChargeWindow*Chg_bySOC ! 夜间、工作日、未满罐且低于补冷阈值时，进入蓄冷模式
TankMode = LoadWindow*Dch_bySOC      ! 白天优先水箱释冷；只要水箱未空，就不开基载冷机
ChillerMode = LoadWindow*(1-Dch_bySOC) ! 白天水箱不可用或已空时，立即切换为冷机直供

HighLoad = ge(LoadKW,1500)       ! 冷机台数判据：LoadKW >= 1500 kW 时启动两台基载冷机；已按新要求替代 1550 kW
OneChillerMode = ChillerMode*(1-HighLoad) ! 冷机直供且负荷低于 1500 kW：只开冷机1
TwoChillerMode = ChillerMode*HighLoad     ! 冷机直供且负荷达到 1500 kW：冷机1+冷机2 同开
```

### 3.1 蓄冷机、蓄冷水泵、冷却侧信号

```trnsys
Chiller3_ON = ChargeMode ! Unit 35 蓄冷机3：仅在工作日 0-8 点且水箱需要补冷时开启
Pump32_ON = ChargeMode   ! Unit 32 蓄冷水泵：与蓄冷机3同步，形成 蓄冷机3 -> 蓄冷泵 -> 水箱 Port-2
Tower3_ON = ChargeMode   ! Unit 36 冷却塔3：与蓄冷机3同步，避免冷机开而冷却塔停
CWPump3_ON = ChargeMode  ! Unit 38 冷却水泵3：与蓄冷机3同步，保证冷凝侧流量
```

解释：夜间蓄冷路径为 `蓄冷罐 Outlet-2 -> 蓄冷机3 -> 蓄冷水泵 Unit32 -> 蓄冷罐 Port-2`。当 `TankFull=1` 或 `SOC>=0.92` 时停止；若仍处于 0-8 点且因散热/混合使 SOC 低于 0.92，则自动补冷。

### 3.2 释冷泵与用户侧三档回水泵信号

```trnsys
Pump6_ON = TankMode      ! Unit 6 释冷水泵：水箱优先供冷时开启，冷机直供时关闭
Pump40_ON = OneChillerMode ! Unit 40 小泵：仅单台基载冷机直供时开启，额定流量 150300 kg/h
Pump43_ON = TwoChillerMode ! Unit 43 大泵：仅双台基载冷机直供时开启，额定流量 300600 kg/h
Pump33_ON = TankMode       ! Unit 33 水箱泵：仅水箱释冷时开启，额定流量 322200 kg/h
```

泵选择依据：

| 模式 | 应开启泵 | 额定流量 | 额定功率 | 判断依据 |
|---|---:|---:|---:|---|
| 水箱释冷 | Unit 6 释冷泵 + Unit 33 水箱泵 | 322200 kg/h | 130000 kJ/h | 匹配蓄冷罐释冷流量 |
| 1 台冷机直供 | Unit 40 小泵 + Unit 10 | 150300 kg/h | 60700 kJ/h | 匹配单台 1400 kW 冷机流量 |
| 2 台冷机直供 | Unit 43 大泵 + Unit 10 + Unit 13 | 300600 kg/h | 126000 kJ/h | 精确匹配两台冷机设计总流量 |

当前三档泵配置已消除原先“322200 kg/h 大泵兼作双冷机回水泵”造成的 7.2% 流量偏差。双冷机直供时 Unit 43 输出 300600 kg/h，经 Unit 14 分流阀 `gam=0.5` 后两台冷机各约 150300 kg/h；水箱释冷时 Unit 33 输出 322200 kg/h，单独匹配蓄冷罐释冷流量。该配置在水力一致性上比两档泵折中方案更严谨，适合作为论文或审稿场景下的推荐方案。

### 3.3 基载冷机、冷冻水泵、冷却塔和冷却水泵信号

```trnsys
Chiller1_ON = min(1,OneChillerMode+TwoChillerMode) ! Unit 9 冷机1：所有冷机直供模式均开启，并限幅到 0-1
Chiller2_ON = TwoChillerMode                       ! Unit 12 冷机2：仅 LoadKW >= 1500 kW 时开启

Pump10_ON = Chiller1_ON ! Unit 10 供冷水泵-1：与冷机1同步
Pump13_ON = Chiller2_ON ! Unit 13 供冷水泵-2：与冷机2同步

Tower1_ON = Chiller1_ON  ! Unit 18 冷却塔1：与冷机1同步
CWPump1_ON = Chiller1_ON ! Unit 19 冷却水泵1：与冷机1同步
Tower2_ON = Chiller2_ON  ! Unit 21 冷却塔2：与冷机2同步
CWPump2_ON = Chiller2_ON ! Unit 20 冷却水泵2：与冷机2同步
```

解释：白天水箱还有可用冷量时，`Chiller1_ON=0`、`Chiller2_ON=0`，对应冷却塔和冷却水泵也关闭；水箱耗尽后，冷机信号立即根据 `LoadKW` 切换。

### 3.4 分流阀控制信号

```trnsys
Div14_gam = 0.5*TwoChillerMode ! Unit 14 分流阀-2：单冷机时 gam=0 全走冷机1；双冷机时 gam=0.5 平分到冷机1/2
Div29_gam = ChillerMode        ! Unit 29 分流阀-3：水箱释冷时 gam=0 回水进水箱；冷机直供时 gam=1 全流入管道-4
```

Unit 14 路径：

- `Div14_gam=0`：`outlet1=100%`，全部流入冷机1，冷机2关闭。
- `Div14_gam=0.5`：`outlet1=50%`、`outlet2=50%`，两台冷机平分流量。

Unit 29 路径：

- `Div29_gam=0`：`outlet1=100%`，回水流回蓄冷罐 Port-1，完成水箱释冷回路。
- `Div29_gam=1`：`outlet2=100%`，回水流入管道-4，再经 Unit 14 分配到基载冷机。

## 4. 建议接线表

| 设备 | 当前输入位置 | 建议信号 |
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

## 5. 宏观策略自检

1. 工作日 0:00-8:00：若水箱未满且 SOC 低于补冷阈值，开启蓄冷机3、蓄冷水泵、冷却塔3、冷却水泵3；用户侧泵和基载冷机关闭。
2. 工作日 8:00-22:00：若水箱有冷量，优先走水箱释冷，冷机1/2及其冷却塔、冷却水泵均关闭。
3. 工作日 8:00-22:00 且水箱耗尽：立即切换到基载冷机直供；`LoadKW < 1500` 时只开冷机1，`LoadKW >= 1500` 时开冷机1+2。
4. 周末：`IsWorkday=0`，无蓄冷、无供冷；若负荷文件为 0，所有主动设备应关闭。
5. 用户侧三档泵互斥开启：水箱释冷只开 Unit 33 水箱泵，单冷机直供只开 Unit 40 小泵，双冷机直供只开 Unit 43 大泵。三泵出口经 Unit 42 混合器汇入 Unit 29，不能同时开启，否则会造成用户侧过流。
6. 分流方向：Unit 14 单冷机时必须 `gam=0`，否则会误把水送入关闭的冷机2；Unit 29 水箱释冷时必须 `gam=0`，冷机直供时必须 `gam=1`。

## 6. 仍需注意的科学性问题

1. `WeekdayOffset` 必须校准。当前仿真 `START=3216 h`，若负荷文件首日不是模型默认周一，应调整 `WeekdayOffset`，否则工作日/周末判断会错位。
2. 1500 kW 台数阈值与单台 1400 kW 额定冷量仍存在边界冲突。虽然三档泵已解决流量匹配问题，但冷机容量边界仍需解释为工程控制死区，或确认性能文件在该工况下可提供接近 1500 kW 的冷量。
3. 当前水箱满/空判断依赖节点 1、13、25。若 Type534 数据文件中节点方向或 Port 高度被修改，应重新确认节点 1 是否代表冷端，否则 `TankFull/TankEmpty` 逻辑会反向。
4. Unit 42 为三入口混合器。由于三档泵控制逻辑应互斥，Unit 42 正常只接收一个非零流量入口；若仿真输出显示两个以上入口同时有流量，应优先检查 `Pump33_ON/Pump40_ON/Pump43_ON` 是否被误接或信号未限幅。

## 7. 自评分与可落地改进建议

**自评分：92/100。**

加分原因是：三档泵配置消除了原先双冷机模式 7.2% 的用户侧流量偏差，水力逻辑更严谨。扣分仍来自两点：未实际运行 TRNSYS 得到供回水温度、泵流量和设备启停序列；SOC 补冷逻辑仍未使用真正的状态滞回控制器。

三点可落地改进：

1. 增加输出监测：把 `ChargeMode`、`TankMode`、`ChillerMode`、`Chiller1_ON`、`Chiller2_ON`、`Pump33_ON`、`Pump40_ON`、`Pump43_ON`、`Div14_gam`、`Div29_gam`、`SOC` 接入 Type65 或 Printer，检查 15 min 时间步启停序列是否符合 0-8/8-22 策略。
2. 做一次阈值敏感性分析：将 `SOC_Recharge` 分别设为 0.90、0.92、0.95，对比蓄冷机启停次数、夜间耗电量和日间供水温度，选择不频繁启停且供冷可靠的阈值。
3. 校核三档泵互斥性：重点检查 Unit 42 三个入口流量，水箱释冷时应仅 Unit 33 为 322200 kg/h，单冷机时应仅 Unit 40 为 150300 kg/h，双冷机时应仅 Unit 43 为 300600 kg/h。
