# 基于 Type682 独立负荷端的风冷冷水中央空调 TRNSYS 完整系统搭建指南

## 1. 结论与方案权衡

### 1.1 推荐方案

本阶段建议采用以下系统边界：

```text
15 min 建筑总冷负荷文件 Type9
              |
              v
风冷冷水机组 Type655 -> 等效建筑负荷端 Type682 -> 变频冷冻水泵 Type110
       ^                                                |
       |________________________________________________|

上海气象 Type15 -> Type655 室外干球温度
Equation -> 冷冻水设定温度、最小启停信号
Type25c/Type65c -> 结果输出与在线检查
```

这是一个**完整的冷源侧/冷冻水侧系统模型**，适合研究：

- 风冷冷水机组容量；
- 冷冻水设计流量；
- 机组负荷率与 COP；
- 冷机和水泵电耗；
- 负荷未满足量；
- 后续多机并联、蓄冷或控制策略。

Type682 在这里不是建筑热平衡模型，也不再计算房间温湿度。更准确的名称应是“**等效建筑冷负荷端**”：它把已由 Type56 求得的总冷负荷作为热量加入冷冻水，使供水升温为回水。

### 1.2 为什么第一版不沿用 Type996、Type508 和 Type146

`load_year_15min_new.csv` 已经是全部热区的显热和潜热总冷负荷。若再配置 Type996 风机盘管、Type508 新风冷却除湿盘管和 Type146 新风机，并让这些末端再次根据空气状态求冷量，会出现两个问题：

1. 当前独立模型没有 Type56 的房间回风温度、含湿量和相对湿度，Type996/508 缺少必要边界；
2. 建筑显热、潜热和新风负荷可能被 Type682 与空气侧盘管重复计算。

因此，第一版应删除空气侧耦合，只保留一个 Type682 作为全楼等效末端。后续只有在能够分别提供逐区显热负荷、潜热负荷、回风状态和新风状态时，才有理由恢复 Type996/508/146。

### 1.3 Type 选择建议

| 功能 | 首选 Type | 选择理由 | 暂不选方案 |
|---|---|---|---|
| 负荷文件读取 | Type9e | 现有模型已使用，支持 15 min 自由格式数据 | 不需要把数据改写成 Type14 时间表 |
| 等效建筑负荷端 | Type682 | 直接对水流施加 `kJ/h` 负荷，符号与现有数据一致 | 不用 Type56，不用 Type996 反算负荷 |
| 风冷冷水机组 | Type655 | 与 `air_con` 现有制冷方式一致，明确输出容量、功率、COP 和 PLR | Type666 是水冷冷机，需要冷却塔，不符合本阶段风冷方案 |
| 冷冻水泵 | Type110 | 支持连续控制，后续可自然扩展变流量 | Type114 可用于定流量，但既有项目曾出现质量平衡报警 |
| 气象 | Type15 | 给 Type655 提供室外干球温度 | 本模型不需要太阳辐射计算链 |
| 输出 | Type25c + Type65c | Type25c 便于形成可复核时序文件，Type65c 便于在线看趋势 | 不能只看在线图而不保存数据 |

## 2. 模型边界、假设与成功标准

### 2.1 建模假设

1. `load_year_15min_new.csv` 每行是一个 15 min 时间区间的**平均冷负荷率**，单位为 `kJ/h`，不是该 15 min 内累计的 `kJ`。
2. 文件中的冷负荷为正值，已经包含全部热区显热和潜热，不再额外乘以 4，也不再增加新风负荷。
3. Type682 代表冷冻水在建筑末端吸收的总热量；不再求房间温湿度、末端风量和凝结水量。
4. 第一版用一台等效 Type655 表示整个风冷冷水机组群。多机台数和正式设备参数在系统跑通后确定。
5. 第一版采用定供水温度、定流量和最小启停逻辑，只用于建立守恒、稳定的完整系统。
6. 不研究管网压降时，不用 Type31 假装进行完整水力计算；TRNSYS 的该类热管道模型不能替代管网阻力和泵扬程计算。

### 2.2 当前数据审查结果

| 项目 | 审查结果 |
|---|---:|
| 数据行数 | 35,041 |
| 时间分辨率 | 0.25 h |
| 理论覆盖时间 | 0 至 8,760 h，包含终点 |
| 最小值 | 0 kJ/h |
| 最大值 | 11,143,328.98 kJ/h |
| 峰值冷负荷 | 3,095.37 kW |
| 非零数据点 | 14,505 |
| 负值数据点 | 0 |
| 按 15 min 积分的总冷量 | 约 4,987,730.65 kWh，即 4.988 GWh |

峰值换算为：

```text
Q_peak = 11,143,328.98 / 3600
       = 3,095.37 kW
```

以水比热 `4.19 kJ/(kg.K)`、设计温差 5 K 为结构搭建流量：

```text
m_design = 11,143,328.98 / (4.19 x 5)
         = 531,901 kg/h
         = 531.9 m3/h（按 1000 kg/m3）
```

此流量只用于先跑通系统，不代表最终泵选型结论。

### 2.3 本阶段成功标准

系统只有同时满足下列条件才算“搭建完整”：

1. Type9 输出与 CSV 指定行在时间上完全对齐；
2. Type682 冷负荷满足量与 Type9 输入一致；
3. 冷冻水全环路每个组件的质量流量一致；
4. Type655 能把回水降到设定温度，或明确输出未满足冷量；
5. 能量平衡误差满足约定阈值；
6. 日志无 Fatal、无泵质量平衡报警、无持续不收敛；
7. 时序文件至少保存负荷、供回水温度、流量、冷机冷量、冷机功率、COP、PLR 和泵功率。

## 3. 目标目录现状与应保留内容

`S3_central_air_single2/Project11.tpf` 当前已有：

- Unit 22 Type9：读取 `load_year_15min_new.csv`；
- Unit 4 Type682：负荷已接入，但入口温度和流量未连接；
- Unit 23 Type15：上海气象文件；
- Unit 36 Type9：CO2 数据读取。

其中 Type9 -> Type682 的负荷方向正确。Type682 当前尚未形成水环路，所以只能读取负荷，不能代表中央空调系统。

本任务与 CO2 无关。Unit 36 可以暂时保留但不参与任何连接；为了保持模型最小化，也可在复制出的工作版本中删除。不要改动原始 CSV。

## 4. 在 TRNSYS Studio 中放置组件

建议先另存为：

```text
S3_central_air_single2/Project11_central_air_stage1.tpf
```

不要直接覆盖当前 `Project11.tpf`，这样可以随时比较 Type9/Type682 原始设置。

### 4.1 组件清单

| 建议名称 | Type | Studio 路径或现有来源 | 数量 |
|---|---:|---|---:|
| `LoadReader` | 9e | Utility / Data Readers / Generic Data Files / Expert Mode / Free Format | 1 |
| `BuildingLoad` | 682 | Loads and Structures (TESS) / Flowstream Loads / Other Fluids | 1 |
| `AirCooledChiller` | 655 | HVAC Library (TESS) / Chillers / Air-Cooled Chiller | 1 |
| `CHWPump` | 110 | Hydronics / Pumps / Variable Speed | 1 |
| `Weather` | 15 | Weather Data Reading and Processing | 1 |
| `SystemEquation` | Equation | Assembly / Insert New Equation | 1 |
| `ResultPrinter` | 25c | Output / Printer | 1 |
| `OnlinePlotter` | 65c | Output / Online Plotter With File | 1，可选 |

### 4.2 Studio 图面布局

建议按真实能量流从左到右布置：

```text
                         Weather(Type15)
                               |
                               v
CHWPump(Type110) -> AirCooledChiller(Type655) -> BuildingLoad(Type682)
       ^                                                |
       |________________________________________________|

LoadReader(Type9) ------------------------------------> Load
SystemEquation --------------------> 泵控制、冷机控制、供水设定温度
```

这里将泵放在冷机上游。泵向水中加入的热量会进入冷机负荷，冷机出口才是供水温度，能量边界更清楚。

## 5. 逐组件设置

## 5.1 Type9e 负荷读取

### 推荐的第一版时间策略：先跑全年

为消除跳行歧义，第一版建议：

```text
START = 0
STOP  = 8760
STEP  = 0.25
Header Lines to Skip = 0
```

Type9e 参数建议：

| 参数 | 建议值 | 说明 |
|---|---:|---|
| Mode | 2 | 沿用当前 Expert Mode 设置 |
| Header Lines to Skip | 0 | CSV 没有表头 |
| No. of values to read | 1 | 只有一列负荷 |
| Time interval of data | 0.25 h | 与数据一致 |
| Interpolate or not | 0 | 若每行是 15 min 区间平均负荷，采用阶梯保持 |
| Multiplication factor | 1.0 | 数据已经是 kJ/h |
| Addition factor | 0 | 不加偏置 |
| Average or instantaneous | 1 | 按当前模型的平均值口径 |
| Free format mode | -1 | 沿用当前自由格式设置 |

若原始数据实际上是每个时刻的瞬时采样值，而不是区间平均值，才把 `Interpolate or not` 改为 1。必须在文档中固定一种口径，不能为追求曲线平滑而随意插值。

### 只跑供冷期时

当前模型为：

```text
START = 3216
STOP  = 6552
STEP  = 0.25
Header Lines to Skip = 12865
```

`3216 x 4 + 1 = 12865` 的计算有合理性，但 Type9 的“跳过行数”可能使结果再向后偏一行。必须进行下列哨兵测试：

| TRNSYS 时间 | 检查内容 |
|---:|---|
| 3216.00 h | `[22,1]` 必须等于 CSV 中该时刻的目标值 |
| 3216.25 h | `[22,1]` 必须等于紧接的下一行 |
| 若整体偏后 0.25 h | 把 Skip 从 12865 改为 12864 后重测 |

第一版不建议一边调系统、一边保留这个未验证的时间偏移。

## 5.2 Type682 等效建筑负荷端

参数：

```text
Fluid Specific Heat = 4.190 kJ/(kg.K)
```

输入连接：

| Type682 输入 | 来源 | 第一版说明 |
|---|---|---|
| Inlet Temperature | Type655 Output 1 `Outlet Fluid Temperature` | 冷冻水供水温度 |
| Inlet Flowrate | Type655 Output 2 `Outlet Fluid Flowrate` | 冷冻水流量 |
| Load | Type9 Output 1 | 直接连接，倍率为 1，正号不变 |
| Minimum Heating Temperature | 常数 `-999` | 第一版不限制供热 |
| Maximum Cooling Temperature | 常数 `999` | 第一版先不截断负荷 |

Type682 的关键输出编号：

| 输出编号 | 输出名称 | 用途 |
|---:|---|---|
| 1 | Outlet Temperature | 建筑侧回水温度 |
| 2 | Outlet Flowrate | 环路流量 |
| 3 | Heating Load Met | 本模型应为 0 |
| 4 | Cooling Load Met | 实际施加到水流的冷负荷 |
| 5 | Heating Load Met by Auxiliary | 本模型应为 0 |
| 6 | Cooling Load Met by Auxiliary | 第一版温度上限为 999 时应为 0 |

Type682 的基本校核式为：

```text
Q682 = m x Cp x (T682,out - T682,in)
```

其中 `Q682`、Type9 和 Type682 Output 4 的单位均为 `kJ/h`。

## 5.3 Type110 冷冻水泵

第一版只要求它建立稳定流量边界，不进行泵选型。

| 参数 | 占位值 | 说明 |
|---|---:|---|
| Rated flow rate | 531,900 kg/h | 由峰值负荷和 5 K 温差计算，仅用于结构调试 |
| Fluid specific heat | 4.19 kJ/(kg.K) | 与 Type682、Type655 一致 |
| Rated power | 225,400 kJ/h | 可暂沿用 S3 既有泵值，后续按扬程和效率重算 |
| Motor heat loss fraction | 0 | 第一版沿用既有设置 |
| Power coefficients | 先沿用 S3 的 4 个系数 | 本阶段不评价变频泵能效 |

输入连接：

| Type110 输入 | 来源 |
|---|---|
| Inlet fluid temperature | Type682 Output 1 |
| Inlet fluid flow rate | Type682 Output 2 |
| Control signal | `PumpCtrl`，结构测试时先用 1 |
| Total pump efficiency | 初值 0.6，结构测试暂不研究 |
| Motor efficiency | 初值 0.9，结构测试暂不研究 |

输出：

| 输出编号 | 含义 |
|---:|---|
| 1 | 泵出口水温 |
| 2 | 泵出口流量 |
| 3 | 泵功率，kJ/h |
| 4 | 加入水中的热量，kJ/h |
| 5 | 散向环境的热量，kJ/h |

Type110 会检查入口流量和按控制信号形成的出口流量是否一致。若出现 `Pump mass balance failed`，不能忽略；应检查全环路流量连接、额定流量和控制信号，而不是增加迭代次数掩盖问题。

## 5.4 Type655 风冷冷水机组

Type655 输入连接：

| 输入 | 来源 | 含义 |
|---|---|---|
| Chilled Water Inlet Temperature | Type110 Output 1 | 含建筑负荷和泵热后的回水 |
| Chilled Water Flowrate | Type110 Output 2 | 环路质量流量 |
| Set Point Temperature | `TchwSet` | 第一版固定 7 C |
| Ambient Temperature | Type15 Output 1 | 上海室外干球温度 |
| Chiller Control Signal | `ChillerCtrl` | 结构测试先用 1 |

Type655 必须填写额定容量，不能留空。为了只验证拓扑，可以暂用：

```text
Rated Capacity = 1.15 x 11,143,328.98
               = 12,814,828 kJ/h
               = 3,559.67 kW
Rated COP      = 3.2
Cp             = 4.19 kJ/(kg.K)
```

这只是保证第一版在峰值时不因容量不足而干扰拓扑验证，**不是最终设备规模结论**。正式选型时应改成多台模块机组、考虑同时使用系数、备用率、部分负荷性能和厂家工况表。

外部性能文件可先复用 `air_con` 现有 Type655 使用的：

```text
AirCooledChiller/Samp_C.Dat
AirCooledChiller/Samp_PLR.Dat
```

需要确认这些表的室外温度、冷冻水出水设定温度和 PLR 范围覆盖实际运行点。路径优先在 Studio 中选择并保存为可迁移设置，不要把其他电脑上的绝对路径写进交付模型。

Type655 的关键输出：

| 输出编号 | 输出名称 | 单位 |
|---:|---|---|
| 1 | Outlet Fluid Temperature | C |
| 2 | Outlet Fluid Flowrate | kg/h |
| 3 | Chiller Power | kJ/h |
| 4 | Available Capacity | kJ/h |
| 5 | COP | - |
| 6 | Load Required to Reach Setpoint | kJ/h |
| 7 | Load Met | kJ/h |
| 8 | Part Load Ratio | - |
| 9 | Fraction of Full Load Power | - |
| 10 | Heat Rejection | kJ/h |

当 Type655 容量不足时，Output 1 会高于 `TchwSet`，Output 7 小于 Output 6。不能只看“冷机已经开启”就认定负荷已满足。

## 5.5 Type15 气象

本模型只需要 Type15 的室外干球温度接 Type655。可继续使用当前上海文件：

```text
D:\Trnsys18\Weather\Meteonorm\Asia\CN-Shanghai-583670.tm2
```

建议在项目备注中记录气象文件来源和版本。若项目需要迁移，应把气象依赖统一整理，而不是依赖某台电脑的绝对盘符。

当前 Type15 关于太阳落山后辐射或水平辐射修正的少量警告，与本模型的 Type655 干球温度输入没有直接关系，但仍应保留在日志说明中。

## 6. 完整连接顺序

在 Studio 中按下表逐条连接，不要用未连接输入的初始值长期代替正式连接。

| 序号 | 上游输出 | 下游输入 |
|---:|---|---|
| 1 | Type9 Output 1 | Type682 Load |
| 2 | Type655 Output 1 | Type682 Inlet Temperature |
| 3 | Type655 Output 2 | Type682 Inlet Flowrate |
| 4 | Type682 Output 1 | Type110 Inlet fluid temperature |
| 5 | Type682 Output 2 | Type110 Inlet fluid flow rate |
| 6 | Type110 Output 1 | Type655 Chilled Water Inlet Temperature |
| 7 | Type110 Output 2 | Type655 Chilled Water Flowrate |
| 8 | Type15 Output 1 | Type655 Ambient Temperature |
| 9 | `TchwSet` | Type655 Set Point Temperature |
| 10 | `ChillerCtrl` | Type655 Chiller Control Signal |
| 11 | `PumpCtrl` | Type110 Control signal |

连接完成后的质量流闭环应为：

```text
Type110 Output 2
= Type655 Input/Output flow
= Type682 Input/Output flow
= Type110 Inlet flow
```

## 7. 第一版 Equation

### 7.1 结构连通测试

第一次只跑 24 至 72 h 时，采用最简单的常量：

```trnsys
TchwSet = 7.0
PumpCtrl = 1.0
ChillerCtrl = 1.0
```

这一步不用于评价节能，只验证：

- 水路闭合；
- 质量流量守恒；
- Type682 正确升温；
- Type655 正确降温；
- 各输出单位正确。

### 7.2 最小启停逻辑

结构测试通过后再改为：

```trnsys
Qload = [22,1]
PlantOn = GT(Qload,1.0)
TchwSet = 7.0
PumpCtrl = PlantOn
ChillerCtrl = PlantOn
```

这里的 `1.0 kJ/h` 仅用于把数值零与正负荷区分开。此逻辑没有回差、最小开机时间、最小停机时间和分级启停，不能作为最终控制策略。

### 7.3 建议同时建立的诊断变量

假设 Unit 编号仍为当前 Type9 `22`、Type682 `4`，新增 Type655 和 Type110 的 Unit 编号以 Studio 实际编号替换：

```trnsys
Load_kW = [22,1]/3600
Load682_kW = [4,4]/3600
Aux682_kW = [4,6]/3600
ChillerPower_kW = [Type655Unit,3]/3600
ChillerLoadMet_kW = [Type655Unit,7]/3600
PumpPower_kW = [Type110Unit,3]/3600
PlantPower_kW = ChillerPower_kW + PumpPower_kW
ChillerUnmet_kW = MAX(0,([Type655Unit,6]-[Type655Unit,7])/3600)
```

TRNSYS Equation 中不能直接使用 `Type655Unit` 这样的文字占位符。实际输入时必须替换为 Studio 生成的数字 Unit 编号。

## 8. 输出变量与结果文件

Type25c 建议至少输出：

| 类别 | 变量 |
|---|---|
| 时间与输入 | TIME、Type9 Output 1、`Load_kW` |
| Type682 | Output 1、2、4、6 |
| Type110 | Output 1、2、3、4 |
| Type655 | Output 1 至 10，至少保留 1、3、4、5、6、7、8、10 |
| 控制 | `PlantOn`、`PumpCtrl`、`ChillerCtrl`、`TchwSet` |
| 汇总 | `PlantPower_kW`、`ChillerUnmet_kW` |

建议输出文件使用相对路径和明确名称，例如：

```text
stage1_central_air_15min.out
```

Type65c 在线图建议分两张：

1. 供水温度、Type682 回水温度、`TchwSet`；
2. 建筑负荷、冷机满足冷量、冷机功率、泵功率。

不要把温度和 MW 级功率放在同一坐标轴上判断。

## 9. 分阶段运行与验收

### 阶段 A：无负荷水路测试

将 Type682 Load 暂时接常数 0，运行 24 h。

预期：

- Type110、Type655、Type682 流量完全一致；
- Type655 无冷量需求时功率应为 0；
- 若泵开启，泵热进入回水后可能使冷机产生少量负荷；
- 日志无质量平衡和收敛错误。

### 阶段 B：恒定负荷测试

把 Type682 Load 暂时接常数：

```text
3,600,000 kJ/h = 1,000 kW
```

在 `m = 531,900 kg/h`、`Cp = 4.19` 下，Type682 理论温升为：

```text
DeltaT = 3,600,000 / (531,900 x 4.19)
       = 1.616 K
```

若 Type655 供水为 7.0 C，则 Type682 回水应约为 8.62 C，不计泵和其他热损失。该测试能迅速发现单位、符号和流量错误。

### 阶段 C：选取一个真实日

连接 Type9，先运行 24 至 72 h 的真实负荷片段。

检查：

- 负荷上升时 Type682 回水温度上升；
- 冷机负荷和功率同向变化；
- PLR 位于 0 至 1；
- 冷机不越出性能表；
- 供水温度没有非物理突跳；
- Type9 与 CSV 时间对齐。

### 阶段 D：完整供冷期或全年

短期测试全部通过后再运行：

```text
START = 0
STOP  = 8760
STEP  = 0.25
```

全年共 35,040 个时间区间。CSV 的 35,041 行包含 0 h 初值/端点，不应把 35,041 再乘 0.25 当成总时长。

## 10. 守恒与可信度检查

### 10.1 Type682 能量平衡

每个非零负荷时步检查：

```text
epsilon_682 = abs(Q_input - m Cp (Tout-Tin)) / max(Q_input,1)
```

在没有温度限幅时，建议 `epsilon_682 < 0.1%`。

### 10.2 全系统能量平衡

稳态、无管道热损失时：

```text
Q_chiller_met ≈ Q_building + Q_pump_to_fluid
```

若以后加入有热容的 Type31、水箱或其他储能组件，则单时步不一定平衡，必须按一段时间积分并计入储能变化。

### 10.3 负荷满足判断

同时检查三项：

```text
Type682 Output 6 = 0
Type655 Output 7 ≈ Type655 Output 6
Type655 Output 1 ≈ TchwSet
```

仅满足其中一项不能证明系统容量充足。

### 10.4 日志验收

允许记录但需说明：

- Type682 在多个 DLL 中重复发现，TRNSYS 使用第一个实例；只要实际加载版本一致，通常不是模型错误；
- Type15 的少量气象辐射修正警告。

不允许忽略：

- `Fatal`；
- `Pump mass balance failed`；
- 性能表长期越界；
- 达到最大迭代次数；
- NaN；
- Type682 辅助冷源持续承担负荷；
- Type655 长期 PLR = 1 且供水温度高于设定值。

## 11. Type31 管道是否现在加入

### 权衡

加入 Type31 的优点是可以表达供回水管的热损失和热惯性；缺点是 15 min 步长、短管长和大流量组合容易出现“时间步内流量超过管内容量”等数值提示，而且 Type31 并不会根据管径自动完成真实压降和泵扬程计算。

### 建议

第一版直接连接：

```text
Type655 -> Type682 -> Type110 -> Type655
```

待阶段 A 至 D 全部通过后，若研究确实需要管损，再加入：

```text
Type655 -> 供水管 Type31 -> Type682 -> 回水管 Type31 -> Type110 -> Type655
```

加入后重新做能量平衡，并把 Type31 的环境温度、长度、管径、保温损失系数和初始温度作为正式参数，而不是随意采用默认值。

## 12. 后续扩展顺序

### 12.1 多台风冷冷水机组并联

单台等效 Type655 跑通后，再按真实设备台数扩展：

```text
回水总管 -> Type11f 分流器 -> Type655-1 / Type655-2 / ...
         -> Type11h 混合器 -> 供水总管 -> Type682
```

每台冷机支路流量、分流比例和启停信号必须守恒。不要在控制逻辑尚未建立时把多台冷机全部复制进模型，否则只会增加代数环和收敛风险。

### 12.2 正式设备规模估计

系统稳定后再决定：

- 单机容量与台数；
- N+1 或其他备用原则；
- 设计供回水温差；
- 冷冻水泵额定流量、扬程和效率；
- 室外温度修正后的制冷量；
- 部分负荷 COP；
- 最小流量、最小 PLR 和旁通；
- 年电耗与峰值电功率。

### 12.3 控制策略

最后加入：

- 负荷分级启停；
- 供水温度重置；
- 变流量控制；
- 最小开停机时间；
- 回差控制；
- 多机均衡运行；
- 极端天气容量校核。

## 13. 本阶段不应做的事情

1. 不把 `kJ/h` 再乘 4；
2. 不把正冷负荷取负后接 Type682；
3. 不同时保留 Type682 总负荷和按同一负荷计算的 Type996/508；
4. 不用 Type56 的负荷结果再次驱动 Type56；
5. 不用未连接输入的初始值长期代替正式连线；
6. 不在单台等效模型尚未守恒时复制多台冷机；
7. 不把 Type655 Output 3 的 `kJ/h` 直接当成 kW；
8. 不把 Type682 的“辅助冷源满足量”误认为冷机实际供冷量；
9. 不因模型能够完成计算就忽略质量平衡、性能表越界和未满足负荷；
10. 不把本模型解释为可以预测房间温湿度或逐区舒适性。

## 14. 最小执行清单

- [ ] 将当前工程另存为 `Project11_central_air_stage1.tpf`
- [ ] 第一版改为全年 `0-8760 h`、`STEP=0.25 h`
- [ ] Type9 跳过 0 行，倍率 1.0，核实插值口径
- [ ] 保留 Type9 -> Type682 Load 正号连接
- [ ] 新增 1 个 Type655
- [ ] 新增 1 个 Type110
- [ ] 连接 `Type655 -> Type682 -> Type110 -> Type655`
- [ ] Type15 干球温度接 Type655 Ambient Temperature
- [ ] 显式连接 `TchwSet`、`PumpCtrl`、`ChillerCtrl`
- [ ] 新增 Type25c 保存完整时序结果
- [ ] 先做无负荷测试
- [ ] 再做 1000 kW 恒负荷测试
- [ ] 再做真实日测试
- [ ] 最后跑完整供冷期或全年
- [ ] 校核 Type682、Type655 和全环路质量/能量守恒
- [ ] 保存并审查 `.log`、`.lst` 和输出文件

## 15. 最终建议

当前最稳妥的技术路线不是把 `air_con` 中 12 层、48 个 Type996、12 个 Type508 和 Type56 的强耦合系统整体复制过来，而是把已经求得的全楼总冷负荷作为系统边界，建立一个单一、守恒、可复核的风冷冷水环路：

```text
Type9 负荷 -> Type682 等效建筑端
Type682 回水 -> Type110 冷冻水泵 -> Type655 风冷冷水机组
Type655 供水 -> Type682
Type15 -> Type655
```

先证明这个最小完整系统在 15 min 时步下质量守恒、能量守恒、时间对齐且负荷可满足，再进行多机并联、正式设备选型和控制优化。这样得到的设备规模和能耗结论才可解释、可复核，也不会与原 Type56 建筑负荷重复计算。
