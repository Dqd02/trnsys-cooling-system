# 净负荷窗口全变频水泵 Unit38 控制 Equation 与系统连线复核

检查日期：2026-07-27  
检查对象：`净负荷窗口/Project11.dck`、`Project11.tpf`、`Project11.log`、`NLF_new.csv`、`load_15min_max2.csv`  
仿真区间：`3216-6552 h`，步长 `0.25 h`

## 1. 结论与关键权衡

当前系统的水路拓扑能够实现“净负荷窗口内负荷优先、余流蓄冷；非窗口优先释冷；余冷不足后双冷机直供”。水箱、Unit35分流、Unit29回水换向以及Unit32/34两条支路的物理连接方向基本正确。

但是，现有Unit38尚未满足最新策略，审查结论为：**不通过，按本报告修改并复跑后再验收**。主要问题如下：

1. 当前 `ChargeWindow=IsWorkday*IsWindow` 会屏蔽周末窗口。当前仿真区间内外部窗口信号共有3328个时步，其中958个在周末；按照新策略，外部窗口应直接决定是否允许蓄冷，不能再乘 `IsWorkday`。
2. 当前负荷流量只增加5%裕度，应改为10%。
3. 当前非窗口余冷不足时只开冷机1；新策略要求两台冷机同时开启，并由Unit56、57各承担一半需求流量。
4. 当前Unit56、57在冷机开启时直接取信号1；新策略要求仅在窗口内取1，非窗口双冷机直供时按负荷变频。
5. 当前Unit58释冷泵直接取0/1信号，实际会输出额定 `430000 kg/h`；应改为按建筑需求流量加10%裕度连续调节。
6. 当前四台冷却水泵与冷机0/1信号同步，非窗口直供时仍为满流量；应与各自供冷泵使用相同归一化信号。
7. 当前Unit32、34虽然额定流量同为 `430000 kg/h`，但它们与Unit56、57的额定流量不同。控制时必须按实际额定流量换算，不能把“单台供冷泵信号”和“支路流量”混为一谈。
8. 最新日志中9台Type110均出现4-14个质量平衡失败时步，同时有22个不收敛时步，当前能耗结果不能直接定稿。

核心权衡：窗口内强制Unit56、57满流量有利于充分利用低净负荷/低碳窗口蓄冷，但当水箱已满且建筑负荷小于总额定流量时，系统没有容纳多余流量的支路。依照您的要求，本报告采用“窗口内水箱已满且有负荷时，将430000 kg/h全部送往建筑”的基准策略；这时建筑流量会高于“负荷需求+10%”，实际供回水温差会小于8 K。若要求建筑流量始终严格等于需求+10%，水箱蓄满后就必须允许Unit56、57降频，或增加旁通支路，两者不能同时满足。

## 2. Model Contract

### 2.1 核心目标

构建一套互斥、守恒且可追踪的Unit38控制，使外部净负荷窗口、建筑负荷、水箱可用状态和全部变频泵协调工作，并确保每个Type110的控制信号均按其自身额定流量换算。

### 2.2 模型输入

| 输入 | 来源 | 单位/范围 | 用途 |
|---|---|---|---|
| 建筑原始负荷 | `[22,1]` | kJ/h | 计算建筑所需冷冻水流量 |
| 净负荷窗口 | `[39,1]` | 0-1 | 决定是否处于蓄冷窗口 |
| 水箱平均温度 | `[7,5]` | °C | 估算SOC |
| 水箱顶部节点 | `[7,18]` | °C | 蓄满判据 |
| 水箱中部节点 | `[7,30]` | °C | 蓄满/放空判据 |
| 水箱底部节点 | `[7,42]` | °C | 放空判据 |
| TRNSYS时间 | `time` | h | 工作日和8-22点负荷门控 |

### 2.3 关键额定流量

| 设备 | Unit | 额定流量 kg/h | 控制信号为 `u` 时的输出流量 |
|---|---:|---:|---:|
| 供冷水泵1 | 56 | 215000 | `215000u` |
| 供冷水泵2 | 57 | 215000 | `215000u` |
| 负荷支路泵 | 32 | 430000 | `430000u` |
| 蓄冷支路泵 | 34 | 430000 | `430000u` |
| 释冷水泵 | 58 | 430000 | `430000u` |
| 冷机1两台冷却水泵 | 54、52 | 399600 | `399600u` |
| 冷机2两台冷却水泵 | 51、55 | 399600 | `399600u` |

由于 `2×215000=430000`，两台供冷泵信号相同时，其合计流量恰好等于一台Unit32/34/58在相同信号下的流量。这是本控制方案可以使用相同归一化流量比例的基础。

## 3. 五种互斥运行工况

| 工况 | 条件 | 冷机 | Unit56/57 | Unit32 | Unit34 | Unit58 | 回水去向 |
|---|---|---|---|---|---|---|---|
| A 窗口蓄冷、无负荷 | 窗口=1、水箱未满、负荷=0 | 两台开 | 均为1 | 0 | 1 | 0 | 水箱回冷机 |
| B 窗口内负荷优先、余流蓄冷 | 窗口=1、水箱未满、有负荷 | 两台开 | 均为1 | `LoadFrac` | `1-LoadFrac` | 0 | 建筑与水箱回水合流后回冷机 |
| C 窗口内水箱已满、仍有负荷 | 窗口=1、水箱满、有负荷 | 两台开 | 均为1 | 1 | 0 | 0 | 建筑回冷机 |
| D 非窗口水箱释冷 | 窗口=0、有负荷、水箱可用 | 两台关 | 0 | 0 | 0 | `LoadFrac` | 建筑回水进入水箱 |
| E 非窗口双冷机直供 | 窗口=0、有负荷、水箱不可用 | 两台开 | 均为 `LoadFrac` | `LoadFrac` | 0 | 0 | 建筑回冷机 |

其中：

```text
LoadFrac = min(1, 含10%裕度的建筑需求流量 / 430000)
```

工况A-E之外均为停机状态。

## 4. 推荐完整 Unit38 Equation

建议把当前49条Equation整体替换为以下64条。变量名保留了当前设备已经连接的 `Pump10_ON`、`Pump13_ON`、`CWPump1_ON`、`CWPump2_ON` 和 `DischargePump6_ON`，因此按本方案修改Unit38后，大部分控制连线不需要重画；这些名称虽然带 `_ON`，实际在Type110上是0-1连续变频信号。

```text
EQUATIONS 64
T_cold_sp = 4 ! 水箱冷态参考温度与冷机冷冻水出水设定值，°C
T_warm_ref = 12 ! 水箱暖态参考温度与设计回水温度，°C
dT_dead = 1 ! 水箱温度判断死区，K
CHW_SP = 4 ! 两台Type666冷机的冷冻水出水设定值，°C
CpW = 4.19 ! 水的定压比热，kJ/(kg·K)
DTCHW = T_warm_ref-T_cold_sp ! 设计供回水温差，当前为8 K
MCHW_TOTAL_R = 430000 ! 两台供冷泵合计额定流量，也是Unit32/34额定流量，kg/h
MCHW_SINGLE_R = 215000 ! 单台Unit56或57额定流量，kg/h
MDCH_R = 430000 ! Unit58释冷泵额定流量，kg/h
HourOfDay = time-24*int(time/24) ! 当前时刻在一天内的小时数，范围0-24
DayNum = int(time/24) ! 当前仿真日序号
WeekIndex0 = DayNum-7*int(DayNum/7) ! 未校准的周内索引，范围0-6
WeekdayOffset = 0 ! 星期偏移量；当前负荷文件口径取0
RawWeekIndex = WeekIndex0+WeekdayOffset ! 加入星期偏移
Weekday = RawWeekIndex-7*int(RawWeekIndex/7) ! 将周内索引归一化为0-6
IsWorkday = lt(Weekday,5) ! 周一至周五为1，周末为0
IsLoadTime = ge(HourOfDay,8)*lt(HourOfDay,22) ! 严格建筑供冷时段[8:00,22:00)
LoadRaw = max(0,[22,1]) ! Unit22读取的非负建筑原始负荷，kJ/h
BuildingLoad = LoadRaw*IsWorkday*IsLoadTime ! 门控后送入建筑端和控制器的负荷，kJ/h
LoadKW = BuildingLoad/3600 ! 建筑负荷由kJ/h换算为kW
HasLoad = gt(LoadKW,5) ! 负荷大于5 kW时为1，过滤数值噪声
LoadWindow = IsWorkday*IsLoadTime*HasLoad ! 工作日8-22点且有有效负荷时为1
WindowSignal = max(0,min(1,[39,1])) ! 将外部净负荷窗口信号限制在0-1
IsWindow = gt(WindowSignal,0.5) ! 外部窗口信号大于0.5时判定为蓄冷窗口
ChargeWindow = IsWindow ! 蓄冷窗口直接采用外部信号，不再乘IsWorkday
SOC_raw = (T_warm_ref-[7,5])/(T_warm_ref-T_cold_sp) ! 按水箱平均温度估算蓄冷SOC
SOC = max(0,min(1,SOC_raw)) ! 将SOC限制在0-1；0为空/暖，1为满/冷
TankFull = lt([7,18],T_cold_sp+0.5)*lt([7,30],T_cold_sp+dT_dead) ! 顶部和中部均接近冷态时判满
TankEmpty = gt([7,42],T_warm_ref-dT_dead)*gt([7,30],T_warm_ref-3) ! 底部和中部均偏暖时判空
Chg_bySOC = lt(SOC,0.95)*(1-TankFull) ! SOC低于0.95且未判满时允许蓄冷
Dch_bySOC = gt(SOC,0.10)*(1-TankEmpty) ! SOC高于0.10且未判空时允许释冷
MREQ = LoadKW*3600/(CpW*DTCHW) ! 不含裕度的建筑需求质量流量，kg/h
MLOAD_REQ = 1.10*MREQ ! 含10%裕度的建筑需求质量流量，kg/h
LoadFrac = min(1,max(0,MLOAD_REQ/MCHW_TOTAL_R)) ! 总需求流量相对430000 kg/h的归一化比例
TankFlowOK = le(MLOAD_REQ,MDCH_R) ! 释冷泵额定流量能够覆盖需求时为1
TankCanCover = Dch_bySOC*TankFlowOK ! 水箱状态和释冷泵流量能力均满足时允许独立释冷
WindowChargeMode = ChargeWindow*Chg_bySOC ! 窗口内且水箱未满时，蓄冷支路有效
WindowLoadMode = ChargeWindow*LoadWindow ! 窗口与建筑负荷同时出现时为1
WindowChillerMode = ChargeWindow*max(Chg_bySOC,LoadWindow) ! 窗口内需要蓄冷或有负荷时两台冷机运行
TankDischargeMode = (1-ChargeWindow)*LoadWindow*TankCanCover ! 非窗口、有负荷且水箱可用时释冷
DirectChillerMode = (1-ChargeWindow)*LoadWindow*(1-TankCanCover) ! 非窗口、有负荷且水箱不可用时双冷机直供
OffMode = (1-WindowChillerMode)*(1-TankDischargeMode)*(1-DirectChillerMode) ! 三种主运行模式均未启用时为1
Chiller1_ON = max(WindowChillerMode,DirectChillerMode) ! 冷机1在窗口制冷或非窗口直供时为1
Chiller2_ON = max(WindowChillerMode,DirectChillerMode) ! 冷机2与冷机1同时开启和关闭
CHWP_Direct_CTRL = DirectChillerMode*LoadFrac ! 非窗口双冷机直供时的单台供冷泵变频比例
CHWP1_CTRL = max(WindowChillerMode,CHWP_Direct_CTRL) ! Unit56：窗口内为1，非窗口直供时按负荷变频
CHWP2_CTRL = max(WindowChillerMode,CHWP_Direct_CTRL) ! Unit57：窗口内为1，非窗口直供时按负荷变频
Pump10_ON = CHWP1_CTRL ! 保留当前Unit56已有连接名称；实际为0-1连续信号
Pump13_ON = CHWP2_CTRL ! 保留当前Unit57已有连接名称；实际为0-1连续信号
CWP1_CTRL = CHWP1_CTRL ! 冷机1冷却水泵采用与供冷泵1相同的归一化信号
CWP2_CTRL = CHWP2_CTRL ! 冷机2冷却水泵采用与供冷泵2相同的归一化信号
CWPump1_ON = CWP1_CTRL ! Unit54和52的控制信号
CWPump2_ON = CWP2_CTRL ! Unit51和55的控制信号
Tower1_ON = Chiller1_ON ! Type126冷却塔1与冷机1同步，信号仅为0或1
Tower2_ON = Chiller2_ON ! Type126冷却塔2与冷机2同步，信号仅为0或1
DCHP_CTRL = TankDischargeMode*min(1,MLOAD_REQ/MDCH_R) ! Unit58按释冷需求加10%裕度变频
DischargePump6_ON = DCHP_CTRL ! 保留当前Unit58已有连接名称
Gamma35 = min(1,WindowLoadMode*(WindowChargeMode*LoadFrac+(1-WindowChargeMode))+DirectChillerMode) ! Unit35流向负荷支路的分流比例
Pump32_CTRL = min(1,WindowLoadMode*(WindowChargeMode*LoadFrac+(1-WindowChargeMode))+DirectChillerMode*LoadFrac) ! Unit32负荷支路泵信号
Pump34_CTRL = WindowChargeMode*(1-LoadWindow*LoadFrac) ! Unit34蓄冷支路泵信号；无负荷为1，有负荷取剩余比例
Gamma29 = min(1,WindowLoadMode+DirectChillerMode) ! Unit29：窗口负荷或冷机直供时回水走出口2回冷机
Gamma14 = 0.5*max(WindowChillerMode,DirectChillerMode) ! Unit14：两台冷机运行时各分50%回水
FlowSplitError = Pump32_CTRL+Pump34_CTRL-CHWP1_CTRL ! 分流守恒监测量，正常应接近0
ModeSumCheck = WindowChillerMode+TankDischargeMode+DirectChillerMode+OffMode ! 模式完备性监测量，正常应等于1
```

### 4.1 Equation数量校验

Unit38标题必须写 `EQUATIONS 64`。不要保留旧49条公式中的任何同名变量，否则会出现重复定义或旧逻辑覆盖。

### 4.2 为什么冷却水泵信号可与供冷泵相同

相同的是归一化信号，不是实际流量：

```text
供冷泵单台流量 = 215000×u
冷却泵单台流量 = 399600×u
冷却水/冷冻水流量比 = 399600/215000 = 1.8586
```

因此在额定工况和同比例部分负荷假设下，该控制能让冷却侧按设计比例带走冷机排热。它仍属于开环比例控制，不是按实际冷凝热或冷却水温差闭环控制；复跑时必须检查冷机冷却水进出口温度和冷却塔出水温度。

## 5. Unit32、34、56、57的严格流量比例

### 5.1 窗口内无负荷

```text
Unit56 = 215000 kg/h
Unit57 = 215000 kg/h
冷机总出水 = 430000 kg/h
Gamma35 = 0
Unit32 = 0
Unit34 = 430000 kg/h
```

### 5.2 窗口内有负荷且水箱未满

设含10%裕度的负荷流量为 `MLOAD_REQ`：

```text
Gamma35 = MLOAD_REQ/430000
Pump32_CTRL = MLOAD_REQ/430000
Pump34_CTRL = 1-MLOAD_REQ/430000
```

因此：

```text
Unit32流量 + Unit34流量
= 430000×Pump32_CTRL + 430000×Pump34_CTRL
= MLOAD_REQ + (430000-MLOAD_REQ)
= 430000 kg/h
```

这与Unit56、57满流量合计 `430000 kg/h` 完全守恒。

### 5.3 非窗口双冷机直供

```text
CHWP1_CTRL = CHWP2_CTRL = MLOAD_REQ/430000
```

注意分母不是单泵的 `215000`，因为每台泵只承担总需求的一半：

```text
单泵信号
= (MLOAD_REQ/2)/215000
= MLOAD_REQ/430000
```

Unit32同样为：

```text
Pump32_CTRL = MLOAD_REQ/430000
```

所以两台供冷泵合计流量与Unit32流量严格相等。

## 6. 峰值负荷校核

当前建筑峰值为 `3140.261 kW`：

```text
MREQ = 3140.261×3600/(4.19×8)
     = 337259.6 kg/h

MLOAD_REQ = 1.10×MREQ
          = 370985.5 kg/h

LoadFrac = 370985.5/430000
         = 0.86276
```

各工况信号如下：

| 设备/信号 | 窗口内有负荷且蓄冷 | 非窗口水箱释冷 | 非窗口双冷机直供 |
|---|---:|---:|---:|
| Unit56、57 | 1 | 0 | 0.86276 |
| Unit32 | 0.86276 | 0 | 0.86276 |
| Unit34 | 0.13724 | 0 | 0 |
| Unit58 | 0 | 0.86276 | 0 |
| 每台冷却水泵 | 1 | 0 | 0.86276 |
| 每台冷却塔 | 1 | 0 | 1 |

峰值时窗口内仍有约 `59014 kg/h` 进入水箱；非窗口直供时每台供冷泵输出约 `185493 kg/h`，每台冷机承担约 `1570.13 kW`，低于2000 kW额定容量。

双泵在10%裕度下可覆盖的最大建筑负荷为：

```text
430000×4.19×8/(3600×1.10) = 3639.8 kW
```

高于当前峰值，流量能力足够。

## 7. 控制信号与输入输出连线清单

### 7.1 冷冻水主回路

```text
Unit31 -> Unit14
Unit14 outlet1 -> Unit9 -> Unit56
Unit14 outlet2 -> Unit12 -> Unit57
Unit56 + Unit57 -> Unit15 -> Unit25 -> Unit35
```

| Unit | 关键输入 | 正确来源/控制信号 | 当前连接 | 判定 |
|---:|---|---|---|---|
| 9 冷机1 | 输入1、2冷冻水 | Unit14输出1、2 | 正确 | 通过 |
| 9 冷机1 | 输入5设定值 | `CHW_SP` | 当前未连接，仅靠初值4 | 建议修改 |
| 9 冷机1 | 输入6开关 | `Chiller1_ON` | 正确 | 通过 |
| 12 冷机2 | 输入1、2冷冻水 | Unit14输出3、4 | 正确 | 通过 |
| 12 冷机2 | 输入5设定值 | `CHW_SP` | 当前未连接，仅靠初值4 | 建议修改 |
| 12 冷机2 | 输入6开关 | `Chiller2_ON` | 正确 | 通过 |
| 14 分流阀 | 输入3控制 | `Gamma14` | 正确 | 通过 |
| 56 供冷泵1 | 输入1、2 | Unit9输出1、2 | 正确 | 通过 |
| 56 供冷泵1 | 输入3控制 | `Pump10_ON=CHWP1_CTRL` | 已连接旧变量 | 更新公式即可 |
| 57 供冷泵2 | 输入1、2 | Unit12输出1、2 | 正确 | 通过 |
| 57 供冷泵2 | 输入3控制 | `Pump13_ON=CHWP2_CTRL` | 已连接旧变量 | 更新公式即可 |

### 7.2 窗口内分流与蓄冷

```text
Unit25 -> Unit35
Unit35 outlet1 -> Unit34 -> Unit7 Port-2（蓄冷）
Unit35 outlet2 -> Unit32 -> Unit26 -> Unit5 -> Unit4（建筑）
```

| Unit | 控制输入 | 正确信号 | 说明 |
|---:|---|---|---|
| 35 分流器 | 输入3 | `Gamma35` | 表示进入outlet2负荷支路的比例 |
| 34 蓄冷支路泵 | 输入3 | `Pump34_CTRL` | 与Unit35出口1流量比例严格一致 |
| 32 负荷支路泵 | 输入3 | `Pump32_CTRL` | 窗口蓄冷时与Gamma35一致；直供时等于LoadFrac |
| 7 水箱Port-2 | 输入温度、流量 | Unit34输出1、2 | 当前正确 |

### 7.3 建筑端与回水换向

```text
Unit26 -> Unit5 -> Unit4 -> Unit28 -> Unit29
Unit29 outlet1 -> Unit7 Port-1（水箱释冷回水）
Unit29 outlet2 -> Unit37 -> Unit31（回冷机）
Unit7 Outlet-2 -> Unit37（蓄冷回水）
```

| Unit | 关键输入 | 正确信号/来源 | 当前状态 |
|---:|---|---|---|
| 4 Type682 | 输入3 Load | `BuildingLoad` | 当前直接接Unit22输出，建议改 |
| 29 回水分流阀 | 输入3 | `Gamma29` | 当前已连接，更新公式即可 |
| 37 合流阀 | 输入1、2 | 水箱Outlet-2 | 正确 |
| 37 合流阀 | 输入3、4 | Unit29 outlet2 | 正确 |

### 7.4 释冷回路

```text
Unit7 Outlet-1 -> Unit58 -> Unit26 -> Unit5 -> Unit4
Unit4 -> Unit28 -> Unit29 outlet1 -> Unit7 Port-1
```

Unit58输入3应保持连接 `DischargePump6_ON`，但该变量必须按推荐Equation定义为连续的 `DCHP_CTRL`，不能再直接等于 `TankDischargeMode`。

### 7.5 冷却水回路

```text
冷机1：Unit9 -> Unit54 -> Unit16 -> Unit18 -> Unit52 -> Unit9
冷机2：Unit12 -> Unit51 -> Unit17 -> Unit21 -> Unit55 -> Unit12
```

| 设备 | Unit | 控制信号 |
|---|---:|---|
| 冷机1塔前冷却泵 | 54 | `CWPump1_ON=CWP1_CTRL` |
| 冷机1塔后冷却泵 | 52 | `CWPump1_ON=CWP1_CTRL` |
| 冷机2塔前冷却泵 | 51 | `CWPump2_ON=CWP2_CTRL` |
| 冷机2塔后冷却泵 | 55 | `CWPump2_ON=CWP2_CTRL` |
| 冷却塔1 | 18 | `Tower1_ON=Chiller1_ON` |
| 冷却塔2 | 21 | `Tower2_ON=Chiller2_ON` |

物理连线正确，没有把冷机1、2的冷却水泵交叉连接。

## 8. 当前系统其他问题

### 8.1 最新日志未通过数值验收

| Unit | 设备 | 质量平衡失败时步 |
|---:|---|---:|
| 34 | 蓄冷支路泵 | 6 |
| 32 | 负荷支路泵 | 8 |
| 54、52 | 冷机1冷却水泵 | 各14 |
| 51、55 | 冷机2冷却水泵 | 各4 |
| 56 | 供冷泵1 | 13 |
| 57 | 供冷泵2 | 4 |
| 58 | 释冷泵 | 11 |

另外有22个不收敛时步。推荐Equation通过同一流量比例统一分流阀和各泵，可减少控制不一致，但仍必须复跑确认上述数量全部降为0。

### 8.2 Type31管道容量警告

Unit5、16、17、25、28、31均报告管内容量不足。根因是15分钟步长远大于短管实际停留时间。若研究目标是全年能耗，不建议通过不合理放大管径解决；应改用无显著容量的连接/管路模型，或接受其为模型结构限制并验证不影响年度能量积分。若研究瞬态温度，则应缩短步长。

### 8.3 水箱初始温度

Unit7的25个节点初温均为15°C，而暖态参考为12°C。控制上会把初始水箱正确判为空，但首个周期不是稳态周期。建议把初温改为12°C，或先预运行若干周期，正式统计时剔除初始化阶段。

### 8.4 水箱可用冷量判据的边界

当前 `TankCanCover` 使用SOC、节点温度和泵流量能力判断，属于可解释的简化控制，不是严格的“剩余kWh足够覆盖下一时步负荷”计算。若需要精确判定余冷是否足够，应按25个节点的水量和温度计算剩余可用冷量，并与下一时步 `LoadKW×0.25 h×1.10` 比较。

### 8.5 Type110低信号功率

全部泵目前使用 `3、0.2、0.3、0.5`，对应：

```text
P/P_rated = 0.2+0.3u+0.5u²，u>0
```

信号刚大于0时功率已接近额定功率的20%，并不是常见的理想立方律。它不影响流量守恒，但会明显影响低负荷能耗。正式比较不同策略前，应使用厂家曲线或至少做功率曲线敏感性分析。

### 8.6 窗口内水箱已满的过流问题

当水箱已满且仍有建筑负荷时，推荐公式按您的“窗口内两台供冷泵信号1”要求，让Unit32取1并把430000 kg/h全部送往建筑。若此时建筑只需要较小流量，这不会额外制造建筑冷负荷，但会降低实际供回水温差并增加泵耗。

更节能的替代方案是：

```text
水箱满且有负荷时：CHWP1_CTRL=CHWP2_CTRL=LoadFrac
Pump32_CTRL=LoadFrac
Gamma35=1
```

该方案更符合变流量系统，但不符合“窗口内水泵始终满功率”的严格表述。本报告未将其写入基准Equation。

## 9. 修改步骤

1. 复制当前TPF和DCK为带日期的备份版本。
2. 在Studio打开Unit38，把旧49条Equation全部删除，粘贴第4节64条新公式，并把Equation数量改为64。
3. 将Unit4第3输入从Unit22输出1改接 `BuildingLoad`。
4. 将Unit9和Unit12第5输入从未连接改接 `CHW_SP`。
5. 检查Unit56、57第3输入仍分别为 `Pump10_ON`、`Pump13_ON`。
6. 检查Unit54、52第3输入均为 `CWPump1_ON`；Unit51、55均为 `CWPump2_ON`。
7. 检查Unit58第3输入为 `DischargePump6_ON`。
8. 检查Unit35、29、14第3输入分别为 `Gamma35`、`Gamma29`、`Gamma14`。
9. 在Type65中增加 `FlowSplitError` 和 `ModeSumCheck`；前者应接近0，后者应恒等于1。
10. 从Studio重新生成DCK并运行整个 `3216-6552 h` 区间。
11. 检查日志：Fatal=0、不收敛时步=0、所有Type110质量平衡失败时步=0。
12. 分别抽查五种工况的信号和流量，确认与第3节完全一致后，再采用能耗和碳排放积分结果。

## 10. 最终验收清单

- 外部窗口信号为1且水箱未满、无负荷：两台冷机/塔为1，Unit56/57/34为1，其余负荷与释冷泵为0。
- 窗口内有负荷且水箱未满：`Pump32_CTRL+Pump34_CTRL=1`，Unit56/57为1。
- 非窗口水箱可用：冷机、塔、冷却泵、Unit56/57均为0，Unit58等于 `LoadFrac`。
- 非窗口水箱不可用：两台冷机和塔均为1，Unit56/57/32均等于 `LoadFrac`。
- Unit54=Unit52=Unit56的控制信号；Unit51=Unit55=Unit57的控制信号。
- Unit14两出口流量相等；Unit56与57流量相等。
- Unit32入口/出口、Unit34入口/出口、Unit58入口/出口均满足质量守恒。
- 工作日8点前、22点后和周末，`BuildingLoad=0`。
- 峰值时 `LoadFrac≈0.86276`，不得超过1。
- 日志无不收敛和泵质量平衡警告。

## 11. 自评与改进建议

自评分：**95/100**。

扣分原因：本报告基于最新DCK、日志和Type110流量关系进行了静态与量纲校核，但推荐Equation尚未由您在Studio中应用并复跑；水箱“余冷足够”的判断仍采用SOC与节点温度代理，而非严格逐时剩余kWh预测。

三点改进建议：

1. **先解决守恒与收敛，再比较能耗。** 将Unit38统一后，要求9台Type110质量平衡警告和22个不收敛时步全部清零，当前能耗文件暂不作为最终结果。
2. **增加水箱能量判据。** 用25节点温度计算可用冷量，并与下一15分钟负荷加10%裕度比较，可避免SOC尚大于0.1但实际不足以覆盖高负荷时仍进入释冷模式。
3. **建立节能对照控制。** 在基准策略之外增加“水箱满后供冷泵按LoadFrac降频”和“低负荷单机、高负荷双机”的对照方案，量化满流量基准策略带来的额外泵耗和低PLR惩罚。
