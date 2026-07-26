# 上海商用办公楼中央空调方案评审与 TRNSYS Type56 建模步骤

## 0. 结论先行

**推荐方案：风冷冷水机组 + 冷冻水循环 + 风机盘管/空调箱末端 + 独立新风除湿。**

在你给定的边界条件下，即“不采用区域集中供冷、不采用分体式空调”，对于上海约 19,190.8 m2、南北两栋各 6 层的商用办公楼，最稳妥的中央空调建模路线不是“风冷式风循环”，而是：

```text
风冷冷水机组 Type655
  -> 冷冻水供回水 7/12 C
  -> 各楼层/功能区风机盘管 Type996
  -> 新风机 Type146 + 新风冷却除湿盘管 Type508
  -> Type56 各 airnode 的送风温度、含湿量、换气次数输入
```

**机组数量不建议全楼只有 1 台。** 工程上 1 台大机组服务全楼会带来冗余差、部分负荷效率差、故障影响大、南北楼负荷差异难控制等问题。更符合市场实际的做法是采用多台模块化风冷冷水机组并联，按南北楼或楼层组分区。

**建议的工程真实方案：**

```text
南楼：2-4 台模块化风冷冷水/热泵机组并联
北楼：2-4 台模块化风冷冷水/热泵机组并联
每栋楼一个冷冻水主环路，每层设支路阀门、末端和新风处理
```

**建议的 TRNSYS 第一版仿真方案：**

```text
先采用“每层 1 台等效 Type655”的简化模型
全楼共 12 台等效 Type655
每层 4 个 Type996 末端 + 1 个 Type146 新风机 + 1 个 Type508 新风盘管
```

这个“每层 1 台 Type655”不是说真实工程一定每层放一台冷水机，而是把每层服务范围等效成一个可控冷源，方便先跑通 Type56 与末端系统的闭环。等单层模型稳定后，再把 12 台等效 Type655 合并成“南楼机组群 + 北楼机组群”或“每 2-3 层一组机组”。

## 1. 基于当前模型的判断

我读取了 `air_con` 目录下的以下文件：

- `大致步骤.md`
- `Untitled_imported.dck`
- `Untitled.inf`
- `SUMMARY.BAL`
- `Type655.txt`
- `Type996.txt`
- `Type146.txt`
- `Type508_v2.txt`

当前模型已经具备这些基础：

- Type56 建筑模型已经建立，建筑位置使用上海气象文件：`CN-Shanghai-583670.tm2`。
- `Untitled.inf` 显示建筑有南楼 `S_*` 与北楼 `N_*` 两组区域，功能区包括办公室 `bgs`、会议室 `hys`、卫生间/厕所 `cs`、走廊 `zl`、连接区 `Connect`。
- 建筑楼层面积大致为每层约 1,599 m2，全楼约 19,190.8 m2。
- Type56 当前已有外部 HVAC 输入变量，例如 `T_hys*`、`W_hys*`、`ACH_hys*`、`T_CS1`、`W_CS1`、`ACH_CS1`、`T_ZL1`、`W_ZL1`、`ACH_ZL1` 等。
- `Untitled_imported.dck` 中已经放入了 Type655、Type996、Type146、Type508，但多数输入还处于 `[unconnected]`。

当前方案里需要特别注意的几个问题：

1. `Untitled_imported.dck` 中第一台 Type655 额定冷量为 `1080000 kJ/h = 300 kW`，这作为每层等效机组是合理起点。
2. 现有 4 个 Type996 的额定总冷量合计约 `529200 + 262800 + 126000 + 219600 = 1137600 kJ/h = 316 kW`，略高于 300 kW。若 4 个末端同时满负荷，冷机容量偏紧；若考虑同时使用系数，则可以接受。
3. 当前 Type146 新风机额定风量为 `300 L/s`。对一层约 1,600 m2 的办公楼层而言，若它承担整层新风，这个数偏小。按办公人员与面积估算，单层新风更可能在 `900-1800 L/s` 量级，具体应按人员密度和规范新风量核算。
4. Type56 内部仍存在 `VENTILATION = VENT_office / VENT_cesuo / VENT_connect` 与 `COOLING = COOL001`。如果外部 Type996/Type508 已经给 Type56 送风制冷，内部 ideal cooling 与内部机械新风需要避免重复计算。

## 2. 三种中央空调路线的权衡

### 2.1 风冷冷水循环系统

系统形式：

```text
风冷冷水机组
冷冻水泵
冷冻水管网
风机盘管/空调箱
独立新风系统
```

优点：

- 不需要冷却塔，适合不想做水冷机房或冷却塔的项目。
- 仍然是标准中央空调水系统，不是分体式空调。
- 末端可以按楼层、朝向、功能区分区控制。
- 对 TRNSYS 很友好：Type655 对应风冷冷水机组，Type996 对应风机盘管，Type508 对应冷却盘管。
- 便于后续增加水泵、阀门、旁通、蓄冷或分时电价控制。

缺点：

- 风冷冷水机组夏季高温工况 COP 通常低于水冷冷水机组。
- 室外机组需要屋面或室外平台，需核查噪声、散热、检修空间、承重和排风短路。
- 上海夏季湿热，新风除湿必须单独认真处理，不能只靠 FCU 随便带过。

结论：

**最推荐。** 对你的建模目标、现有 Type 选择、上海办公楼场景和非集中供冷约束都最匹配。

### 2.2 风冷式风循环系统

这里一般指屋顶式空调机组、风冷直膨空调箱、全空气系统或大风管送风系统。

优点：

- 系统链条短，没有冷冻水系统。
- 设备集成度高，理论上冷源和空气处理都在机组内完成。

缺点：

- 对 19,000 m2 办公楼，全空气风量、风管截面、竖井和吊顶空间压力很大。
- 分区控制不如水系统灵活，南北楼、不同楼层、会议室与办公室差异很难细分。
- 上海湿热气候下，若没有良好的再热或湿度控制，容易出现温度满足但湿度偏高。
- 在 TRNSYS 中若用 DX Coil 直接拼全空气系统，模型会比水系统更难与 Type56 多区域送风逐一耦合。

结论：

**不建议作为本项目主方案。** 除非你的建筑本身就是全空气系统、有明确风管竖井和 AHU 设计，否则这条路线不如风冷冷水系统稳。

### 2.3 水冷冷水机组 + 冷却塔

优点：

- 对上海夏季大负荷办公楼，水冷系统通常能效更好。
- 大型公共建筑中非常常见，设备效率和系统成熟度高。

缺点：

- 需要冷却塔、冷却水泵、补水、排污、水处理和机房。
- 运维复杂度高于风冷系统。
- 如果你把“集中供冷”理解为“集中冷站”，该方案可能会违背你的设定。

结论：

**若追求真实大型办公楼高能效，水冷冷站更强；但在你明确不想采用集中供冷的前提下，不作为第一推荐。**

## 3. 机组数量与分区建议

### 3.1 不建议全楼 1 台

全楼峰值负荷如果约为 3,028 kW，一台 3 MW 级风冷冷水机组或机组组服务全楼存在这些问题：

- 单点故障风险大。
- 南北楼负荷不一致时调节粗糙。
- 低负荷运行时间长，部分负荷效率与启停控制差。
- 管网水力平衡复杂。
- 后续若要做分楼、分层计费或策略优化，不方便。

### 3.2 不建议真实工程严格每层 1 台室外冷水机

一层一台风冷冷水机在仿真里清楚，但真实工程上可能导致：

- 屋面或设备平台数量过多。
- 设备维护点过多。
- 每台机组容量较小，设备选型不一定最优。
- 12 套冷源独立布置的管线和电气复杂度偏高。

因此，要区分“仿真等效方案”和“工程真实方案”。

### 3.3 推荐的工程真实分区

按南北楼分两套冷冻水系统，每套由多台模块化风冷冷水/热泵机组并联：

```text
南楼冷源群：约 1.5 MW，建议 3-4 台模块化机组
北楼冷源群：约 1.5 MW，建议 3-4 台模块化机组
```

如果后续负荷数据证明南北楼或楼层负荷差异明显，可以采用：

```text
南楼低区 1-3F：一组机组
南楼高区 4-6F：一组机组
北楼低区 1-3F：一组机组
北楼高区 4-6F：一组机组
```

### 3.4 推荐的 TRNSYS 建模分阶段

第一阶段：

```text
每层 1 台等效 Type655
共 12 台
每台 300 kW 左右
```

第二阶段：

```text
南楼 6 台等效 Type655 合并成南楼冷源群
北楼 6 台等效 Type655 合并成北楼冷源群
```

第三阶段：

```text
用多台 Type655 并联模拟真实模块机组
增加启停台数控制、最小运行时间、最小流量、旁通和水泵功耗
```

## 4. 容量初算

已知或由现有文件推得：

```text
总空调面积：约 19,190.8 m2
总峰值冷负荷：约 3,028 kW
楼栋/楼层：南北 2 栋，每栋 6 层，共 12 层
平均每层面积：19,190.8 / 12 = 1,599.2 m2
平均每层峰值负荷：3,028 / 12 = 252.3 kW
```

按 10%-20% 设备余量：

```text
每层等效冷机容量：280-300 kW
第一版建议：300 kW
```

冷冻水供回水采用常规 7/12 C：

```text
供水温度：7 C
回水温度：12 C
温差：5 K
水比热：4.19 kJ/(kg K)
```

每层 300 kW 对应冷冻水流量：

```text
m = Q * 3600 / (cp * deltaT)
  = 300 * 3600 / (4.19 * 5)
  = 51,551 kg/h
```

与当前 `Untitled_imported.dck` 中 Type655 初始流量 `51600 kg/h` 基本一致。

## 5. 对当前 `大致步骤.md` 的修正意见

`大致步骤.md` 的大方向是正确的：使用 Type655、Type996、Type146、Type508，并按楼层模板复制。需要修正或强调以下点。

### 5.1 “每层一个 Type655”应表述为等效模型

建议写成：

```text
仿真初期采用每层 1 台等效 Type655，代表该楼层可用冷源能力。
工程方案不必真的每层设置一台冷水机，最终可合并为南/北楼冷源群。
```

### 5.2 新风量需要重新核算

当前 Type146 参数是：

```text
Rated Volumetric Flow Rate = 300 L/s
```

如果只服务一个小区域可以接受；如果服务整层，偏低。建议第一版按如下区间设置：

```text
单层新风量：900-1800 L/s
初始推荐：1200 L/s
人员密集会议楼层：可提高到 1500-2000 L/s
```

严谨做法是按每个 airnode 的人员数和建筑规范新风量逐区计算，避免只按面积粗估。

### 5.3 Type996 额定风量偏大时要分清“循环风”和“新风”

现有 4 个 Type996 风量合计：

```text
8167 + 4056 + 1944 + 3389 = 17556 L/s
```

这对一层 1,599 m2 相当于约 11.0 L/(s m2) 的循环送风量，不是新风量。这个值作为风机盘管/末端循环风量可以接受但偏大，需要用出风温差和显热能力校核；不能把它当作室外新风，否则新风负荷会严重放大。

### 5.4 Type508 当前是 free-floating 模式

当前 `Untitled_imported.dck` 中 Type508 参数：

```text
Mode_Control = 0
```

这意味着它是自由出风，不直接控制出风温度或含湿量。上海夏季湿度高，若要控制新风露点，建议后续改用可控模式：

```text
Mode_Control = 1：控制出风温度
Mode_Control = 2：控制出风含湿量
```

若只想先跑通系统，保持 `Mode_Control = 0` 可以；若要研究室内湿度和除湿，建议用 `Mode_Control = 2` 并给出目标含湿量。

## 6. Type56 侧必须处理的问题

### 6.1 关闭或隔离 ideal cooling

当前 Type56 有 `COOLING = COOL001`，输出 `QCOOL_*` 是理想冷负荷。正式接 Type996 后，应避免 Type56 的理想冷源和外部末端重复制冷。

建议保留两个版本：

```text
版本 A：原始理想冷源模型，用于负荷校核
版本 B：外部 HVAC 耦合模型，关闭 Type56 ideal cooling
```

在版本 B 中：

```text
Cooling power = 0
或取消各 airnode 的 COOLING
或把 cooling setpoint 调到不会触发的高温
```

### 6.2 机械新风不要重复计算

当前 Type56 内有：

```text
VENTILATION = VENT_office
VENTILATION = VENT_cesuo
VENTILATION = VENT_connect
```

若外部 Type146 + Type508 已经处理并送入新风，则 Type56 内部原机械新风应取消或改成由外部输入控制。

建议：

```text
保留 infiltration
取消固定机械 ventilation
改用外部输入 T_SUP、W_SUP、ACH_SUP 作为空调送风/新风入口
```

### 6.3 不建议用 negative gain 代替送风

不要把 Type996 的冷量直接作为负得热塞入 Type56：

```text
不推荐：GAIN_COOL = -Q_Type996
```

原因：

- 潜热和湿度处理会失真。
- 送风温度、送风含湿量、风量失去物理意义。
- 与风机盘管和新风系统的实际运行逻辑不一致。

推荐：

```text
Type996/Type508 输出 T_air_out、W_air_out、Mdot_air
  -> Equation 混合
  -> 换算 ACH
  -> Type56 ventilation / air change 输入
```

## 7. 单层系统拓扑

以南楼 1 层为例，建议先搭一层模板。

```text
Type15 天气
  -> Type655 环境温度输入
  -> Type996 环境空气输入
  -> Type146 新风入口

Type655 风冷冷水机组
  -> 7 C 冷冻水
  -> Type996 办公室
  -> Type996 会议室
  -> Type996 卫生间/厕所
  -> Type996 走廊
  -> Type508 新风盘管
  -> 回水混合
  -> Type655

Type56 对应 airnode
  -> 回风温度/湿度/RH
  -> Type996
  -> 处理后送风
  -> Equation 与新风混合
  -> Type56 对应 T/W/ACH 输入
```

## 8. Type655 参数与连接

Type655 源文件显示其模型为风冷冷水机组，依赖外部 catalog performance data 和 part-load data。

### 8.1 参数

| 参数号 | 含义 | 建议值 |
|---:|---|---:|
| 1 | Rated Capacity | `1080000 kJ/h`，即 300 kW |
| 2 | Rated COP | `3.0-3.3`，第一版可用 `3.2` |
| 3 | Performance Data LU | 指向风冷冷机性能文件 |
| 4 | PLR Data LU | 指向部分负荷性能文件 |
| 5 | Fluid Specific Heat | `4.19 kJ/(kg K)` |
| 6 | Number of Ambient Temperatures | 与性能文件一致 |
| 7 | Number of CHW Set Points | 与性能文件一致 |
| 8 | Number of Part Load Ratios | 与 PLR 文件一致 |

### 8.2 输入

| 输入号 | 含义 | 连接建议 |
|---:|---|---|
| 1 | Chilled Water Inlet Temperature | 本层回水混合温度 `T_CHWR_floor` |
| 2 | Chilled Water Flowrate | 本层冷冻水总流量 `m_CHW_floor` |
| 3 | Set Point Temperature | `7 C` |
| 4 | Ambient Temperature | Type15 室外干球温度 |
| 5 | Chiller Control Signal | `chiller_on`，0/1 |

Type655 的源码逻辑显示：

```text
flow_chw <= 0
或 T_chw_in <= T_chw_set
或 gamma < 0.5
```

任一条件成立时，冷机不制冷。

### 8.3 输出

| 输出号 | 含义 | 用途 |
|---:|---|---|
| 1 | Leaving CHW Temperature | 接 Type996/Type508 水入口 |
| 2 | CHW Flowrate | 流量诊断 |
| 3 | Power | 冷机电耗 |
| 4 | Available Capacity | 当前工况可用容量 |
| 5 | COP | 性能诊断 |
| 6 | Load | 当前冷负荷 |
| 7 | Energy Removed | 实际供冷量 |
| 8 | PLR | 部分负荷率 |
| 9 | FFLP | 满负荷功率比例 |
| 10 | Heat Rejection | 向环境排热 |

## 9. Type996 参数与连接

Type996 是 2 管制风机盘管性能图模型。它不是简单负荷扣减器，而是根据空气入口状态、水入口温度、空气流量比、水流量比和性能文件计算出风状态与冷量。

### 9.1 参数

当前办公室末端示例：

```text
Rated Volumetric Air Flowrate = 8167 L/s
Rated Liquid Flowrate = 25260 kg/h
Rated Total Cooling Capacity = 529200 kJ/h = 147 kW
Rated Sensible Cooling Capacity = 396900 kJ/h = 110 kW
SHR = 0.75
Rated Fan Power = 564 kJ/h = 0.157 kW
```

注意：风机功率看起来偏小。147 kW 末端只有 0.157 kW 风机功率，可能低估末端风机电耗。建议后续按实际风机盘管或空调箱样本校核。

### 9.2 输入

| 输入号 | 含义 | 连接建议 |
|---:|---|---|
| 1 | Fluid Inlet Temperature | Type655 出水温度 |
| 2 | Fluid Flowrate | 本末端冷冻水流量 |
| 3 | Return Air Temperature | Type56 对应 airnode 温度 |
| 4 | Inlet Air Humidity Ratio | Type56 对应 airnode 含湿量 |
| 5 | Inlet Air Relative Humidity | Type56 对应 airnode RH |
| 6 | Inlet Air Pressure | `1 atm` |
| 7 | Fan Pressure Rise | 可先取 `0` |
| 8 | Coil Pressure Drop | 可先取 `0` |
| 9 | Ambient Air Temperature | Type15 室外干球 |
| 10 | Ambient Humidity Ratio | Type15 室外含湿量 |
| 11 | Ambient Relative Humidity | Type15 室外 RH |
| 12 | Heating Control Signal | 制冷季取 `0` |
| 13 | Cooling Control Signal | `cool_i` |
| 14 | Fan Control Signal | `fan_i` |
| 15 | Outside Air Control Signal | FCU 不直接引新风时取 `0` |

Type996 源码中，制冷逻辑为：

```text
Gamma_Cool >= 0.5 且 Flow_Fluid > 0 时才制冷
```

所以控制信号不要长期给 `0.2` 或 `0.3` 这种模糊值。建议用 Type2b 滞回输出 0/1。

### 9.3 输出

| 输出号 | 含义 | 用途 |
|---:|---|---|
| 1 | Fluid Outlet Temperature | 回水混合 |
| 2 | Fluid Flowrate | 回水混合 |
| 3 | Air Outlet Temperature | 送风混合 |
| 4 | Air Outlet Humidity Ratio | 送风混合 |
| 5 | Air Outlet RH | 诊断 |
| 6 | Dry Air Mass Flowrate | 换算 ACH |
| 7 | Air Outlet Pressure | 通常诊断 |
| 8 | Total Cooling Rate | 冷量统计 |
| 9 | Sensible Cooling Rate | 显冷量统计 |
| 10 | Total Heating Rate | 制冷季应为 0 |
| 11 | Fan Power | 风机电耗 |
| 12 | Fan Heat to Air | 可用于能量诊断 |
| 13 | Fan Heat to Ambient | 可用于能量诊断 |
| 14 | Condensate Temperature | 除湿诊断 |
| 15 | Condensate Flowrate | 除湿量 |

## 10. Type146 与 Type508 新风系统

### 10.1 Type146 新风机

Type146 是单速风机，控制信号大于 0.5 时开启。

参数建议：

```text
Humidity Mode = 2
Rated Volumetric Flow Rate = 1200 L/s 起步
Rated Power = 2000-6000 kJ/h，根据风量和压头校核
Motor Efficiency = 0.8-0.9
Motor Heat Loss Fraction = 0-1
```

输入：

| 输入号 | 含义 | 连接建议 |
|---:|---|---|
| 1 | Inlet Air Temperature | Type15 室外干球 |
| 2 | Inlet Air Humidity Ratio | Type15 室外含湿量 |
| 3 | Inlet Air RH | Type15 室外 RH |
| 4 | Air Flow Rate | 上游无风机时可给 0 或初值 |
| 5 | Inlet Air Pressure | `1 atm` |
| 6 | Control Signal | `work_sch` 或 `oa_on` |
| 7 | Pressure Increase | 第一版可取 0 |

输出：

| 输出号 | 含义 | 用途 |
|---:|---|---|
| 1 | Outlet Temperature | Type508 空气入口 |
| 2 | Outlet Humidity Ratio | Type508 空气入口 |
| 3 | Outlet RH | Type508 空气入口 |
| 4 | Outlet Mass Flowrate | Type508 空气流量 |
| 5 | Outlet Pressure | Type508 空气压力 |
| 6 | Power | 新风机电耗 |
| 7 | Heat to Air | 诊断 |
| 8 | Heat to Ambient | 诊断 |

### 10.2 Type508 新风冷却除湿盘管

当前文件使用 Type508a free-floating coil，参数 `Mode_Control = 0`，输入 9 个。

若保持 free-floating：

| 输入号 | 含义 | 连接建议 |
|---:|---|---|
| 1 | Fluid Inlet Temperature | Type655 出水温度 |
| 2 | Fluid Flowrate | 新风盘管水流量 |
| 3 | Air Inlet Temperature | Type146 出口温度 |
| 4 | Air Inlet Humidity Ratio | Type146 出口含湿量 |
| 5 | Air Inlet RH | Type146 出口 RH |
| 6 | Air Flowrate | Type146 出口质量流量 |
| 7 | Air Pressure | Type146 出口压力 |
| 8 | Air-Side Pressure Drop | 第一版可取 0 |
| 9 | Coil Bypass Fraction | `0.05-0.15` |

若要控制新风出风温度或含湿量，改 `Mode_Control > 0` 后会增加第 10 个输入：

```text
Mode_Control = 1：第 10 输入为目标出风温度，建议 14-16 C
Mode_Control = 2：第 10 输入为目标含湿量，建议 0.0085-0.010 kg/kg
Mode_Control = 3：第 10 输入为目标出水温度
```

上海夏季湿度控制建议优先考虑：

```text
Mode_Control = 2
W_Air_Want = 0.009 kg/kg
```

## 11. 控制逻辑建议

每个功能区使用温度滞回，不建议直接用连续比例信号接 `Gamma_Cool`。

办公室/会议室：

```text
T_set = 26 C
T_on = 26.5 C
T_off = 25.8 C
```

走廊/卫生间：

```text
T_set = 27 C
T_on = 27.5 C
T_off = 26.8 C
```

每层冷机启停：

```text
chiller_on = MAX(cool_office, cool_meeting, cool_cs, cool_zl, oa_cooling)
```

水流量：

```text
m_office = m_office_rated * cool_office
m_meeting = m_meeting_rated * cool_meeting
m_cs = m_cs_rated * cool_cs
m_zl = m_zl_rated * cool_zl
m_oa = m_oa_rated * oa_cooling

m_load = m_office + m_meeting + m_cs + m_zl + m_oa
m_min = 0.25-0.30 * m_chiller_rated
m_chiller = chiller_on * MAX(m_load, m_min)
m_bypass = MAX(0, m_chiller - m_load)
```

回水混合：

```text
T_return =
(
  m_office * T_office_w_out
  + m_meeting * T_meeting_w_out
  + m_cs * T_cs_w_out
  + m_zl * T_zl_w_out
  + m_oa * T_oa_w_out
  + m_bypass * T_supply
) / MAX(0.001, m_chiller)
```

## 12. 送风混合与 Type56 输入

以办公室为例：

```text
m_sup_office = m_fcu_office + m_oa_office

T_sup_office =
(
  m_fcu_office * T_fcu_office_out
  + m_oa_office * T_oa_out
) / MAX(0.001, m_sup_office)

W_sup_office =
(
  m_fcu_office * W_fcu_office_out
  + m_oa_office * W_oa_out
) / MAX(0.001, m_sup_office)

ACH_sup_office = m_sup_office / (rho_air * V_zone)
```

其中：

```text
rho_air = 1.2 kg/m3
V_zone = Type56 airnode 体积
```

当前 `Untitled.inf` 中典型区域体积如下：

| 区域 | 单层参考面积 | 体积 |
|---|---:|---:|
| 办公室 bgs | 800 m2 | 3920 m3 |
| 会议室 hys | 400 m2 | 1960 m3 |
| 卫生间/厕所 cs | 99.2 m2 | 486.08 m3 |
| 走廊 zl | 约 300.034 m2 | 1470.17 m3 |

所以办公室若送风干空气质量流量为 20,000 kg/h：

```text
ACH = 20000 / (1.2 * 3920) = 4.25 h-1
```

## 13. 一层模板搭建顺序

### 步骤 1：备份模型

保留当前理想冷负荷版本：

```text
building_ideal_cooling.b18
```

另存 HVAC 耦合版本：

```text
building_hvac_coupled.b18
```

### 步骤 2：处理 Type56

在 TRNBuild 中：

1. 保留围护结构、人员、照明、设备、会议室 schedule。
2. 关闭或隔离 `COOLING = COOL001`。
3. 固定机械新风从 Type56 内部移除，改为外部输入。
4. 为每个功能区建立 `T_SUP`、`W_SUP`、`ACH_SUP` 输入。
5. 输出每个功能区的 `TAIR`、`RH`、`W`、`QCOOL`、`QLATD` 作为诊断。

### 步骤 3：搭 Type655 单冷源闭环

先不接 Type996，只用 Equation 假负荷测试：

```text
T_return = 12 C
m_chiller = 51600 kg/h
T_set = 7 C
gamma = 1
```

检查：

```text
Type655 输出 T_chw_out 接近 7 C
Power > 0
COP 合理
PLR 在 0-1
```

### 步骤 4：接一个 Type996

先接办公室 Type996：

```text
水入口：Type655 output 1
水流量：25260 kg/h * cool_office
回风温度：TAIR_S_bgs1
回风含湿量：Type56 对应 W 输出或估算
回风 RH：Type56 对应 RH 输出
Gamma_Cool：Type2b 滞回输出
Gamma_Fan：同 cool_office 或略提前开启
Gamma_OutsideAir：0
```

检查：

```text
出风温度是否约 12-18 C
回水温度是否高于供水温度
Q_TotalCool 是否小于或接近额定冷量
Flow_Condensate 是否非负
```

### 步骤 5：接 Type146 + Type508

```text
Type15 -> Type146 -> Type508 -> 新风分配 Equation -> Type56
Type655 出水 -> Type508 水入口
Type508 出水 -> 回水混合
```

检查：

```text
Type146 风量是否为 900-1800 L/s 对应的 kg/h 量级
Type508 出风含湿量是否下降
室内 RH 是否能控制在 40%-65% 左右
```

### 步骤 6：四类功能区全部接入

本层四个末端：

```text
FCU_S01_BGS
FCU_S01_HYS
FCU_S01_CS
FCU_S01_ZL
```

分别接入办公室、会议室、厕所、走廊。

### 步骤 7：复制到 12 层

建议命名：

```text
CH_S01 ... CH_S06
CH_N01 ... CH_N06

FCU_S01_BGS, FCU_S01_HYS, FCU_S01_CS, FCU_S01_ZL
PAU_S01_FAN, PAU_S01_COIL
EQ_S01_CTRL, EQ_S01_WATER_MIX, EQ_S01_AIR_MIX
```

## 14. 全楼输出指标

至少输出以下指标：

### 室内环境

```text
每区 TAIR
每区 RH
每区 W
超温小时数：TAIR > 27 C
过冷小时数：TAIR < 24 C
高湿小时数：RH > 65%
```

### 冷源

```text
每台 Type655 Power
每台 Type655 Q_met
每台 Type655 COP
每台 Type655 PLR
全楼冷机电耗
全楼供冷量
```

### 末端

```text
每个 Type996 Q_TotalCool
每个 Type996 Q_SensCool
每个 Type996 Fan Power
每个 Type996 Condensate Flow
```

### 新风

```text
Type146 风机电耗
Type508 新风冷量
Type508 出风温度
Type508 出风含湿量
```

### 能效

```text
冷机电耗 kWh
末端风机电耗 kWh
新风机电耗 kWh
系统总电耗 kWh
单位面积电耗 kWh/m2
系统综合 COP = 总供冷量 / 总电耗
```

## 15. 需要补充确认的信息

为了把模型从“能跑”提升到“可信”，还需要补充这些信息：

1. 上海办公楼采用的室内设计参数：夏季温度、相对湿度、新风标准。
2. 每个 airnode 的人员数量和人员时刻表，尤其会议室。
3. 是否只做制冷，还是也要模拟冬季供热。若冬季也要做，风冷冷水机应改为风冷热泵逻辑或另设热源。
4. 屋面或设备平台是否允许布置风冷模块机，是否有噪声限制。
5. 新风是否采用全热回收，若有应增加热回收 Type。
6. 卫生间是否独立排风。卫生间通常不应简单按普通空调送回风处理，应考虑排风和补风路径。
7. 是否需要水泵能耗。当前方案若只接 Type655/996/508，会低估系统总能耗。
8. Type655 与 Type996 的 catalog data 是否为真实设备样本。当前样本文件只能用于跑通，不宜作为最终工程结论。
9. 是否要做分时电价、需求响应或蓄冷。若要做，冷源分组与水系统应提前预留控制变量。

## 16. 最终建议

第一版按当前 `大致步骤.md` 的思路继续，但把它定义为：

```text
楼层级等效风冷冷水中央空调系统
```

推荐初始配置：

```text
每层：
Type655 x 1，300 kW，7/12 C，51600 kg/h
Type996 x 4，办公室/会议室/厕所/走廊
Type146 x 1，新风量先取 1200 L/s
Type508 x 1，新风冷却除湿盘管
Type2b 若干，温度滞回控制
Equation 若干，水流量、回水混合、送风混合、ACH 换算
Type24/Type65/Printer，统计电耗、供冷量、温湿度
```

跑通后再升级为：

```text
南楼冷源群 + 北楼冷源群
每栋 3-4 台模块化 Type655 并联
增加冷冻水泵、旁通、最小流量、台数控制和新风除湿控制
```

一句话概括：

**用风冷冷水循环系统做中央空调最符合你的约束和 TRNSYS 模块条件；仿真先用每层一台等效 Type655 跑通，工程解释上应归并为南北楼模块化风冷冷水机组群；Type56 中关闭理想冷源和重复新风，用 Type996/Type508 的送风温湿度与风量真实耦合到建筑 airnode。**

