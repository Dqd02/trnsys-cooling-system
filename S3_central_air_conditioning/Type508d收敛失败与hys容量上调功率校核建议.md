# Type508d 收敛失败、会议室 hys 上调与功率参数校核建议

## 0. 先说权衡和结论

你现在遇到的 `TRNSYS Message 441` 属于**迭代未收敛警告**，不是立即停止仿真的致命错误。日志显示：

```text
TRNSYS Message 441:
The inputs to the listed units have not converged at this timestep.
UNITS: 25 30 35 36 37 43
```

涉及单元：

| 单元 | 模块 | 含义 |
|---:|---|---|
| 25 | Type655 | 风冷冷水机组 |
| 30 | Type996 | 办公室风机盘管 |
| 35 | Type996 | 会议室风机盘管 |
| 36 | Type996 | 厕所风机盘管 |
| 37 | Type996 | 走廊风机盘管 |
| 43 | Type508d | 新风处理盘管，出风含湿量控制 |

这个组合说明问题不是单个模块坏了，而是**冷冻水回路 + 四个风机盘管 + 新风除湿盘管 + 冷水机组**形成了强耦合迭代。尤其 Type508d 改为含湿量控制后，盘管会内部求解出风含湿量；它的水流量、出水温度又进入 `T_return_floor`，再反馈到 Type655，Type655 出水温度又反馈给所有末端，容易在开机瞬间或负荷突变时不收敛。

建议不要直接把 Type508d 关掉，而是按下面顺序稳定模型：

1. 先把 Type508d 的设定值和水流量显式、平滑、合理地接入。
2. 再避免 Type508d 与四个 Type996 共用同一个强反馈 `T_return_floor` 造成突变。
3. 然后再上调会议室 hys 末端能力。
4. 最后校核各模块功率和能耗输出。

## 1. 当前模型中已经看到的关键问题

## 1.1 Type508d 水流量已接入，但仍有不稳定点

当前 `Equa-3` 中新增了：

```text
m_oa_coil = [38,1]*4000
```

Type508d 的第 2 输入已经接为：

```text
Input 2 Fluid Flowrate = m_oa_coil
```

这说明你已经把新风盘管冷冻水流量显式连接了。

但当前 Type508d 第 10 输入在 `.dck` 中仍显示为：

```text
0,0    ! [unconnected] Setpoint: Outlet Air Humidity Ratio (w)
*** INITIAL INPUT VALUES
... 0.0095
```

也就是说，从 `.dck` 看，`W_Air_Want = 0.0095 kg/kg` 仍然只是初始值，不是 Equation 显式连接。初始值可以运行，但不利于检查，也不利于后续做变设定值或稳定化。

建议在 `Equa-3` 加：

```text
W_oa_want = 0.0095
```

并把 Type508d 第 10 输入接为：

```text
W_oa_want
```

## 1.2 Message 441 发生在开机附近，说明突变是重要诱因

日志中 Message 441 发生在：

```text
time = 4712.250000
```

你的仿真起始时间是 `4680`，工作日开关 `[38,1]` 是 8-22 点阶跃。`m_oa_coil = [38,1]*4000` 意味着新风盘管水量在开机时从 0 突然跳到 4000 kg/h。与此同时：

```text
m_bgs = 15980*cool_bgs
m_hys = 7940*cool_hys
m_cs  = 3815*cool_cs
m_zl  = 6635*cool_zl
```

四个风机盘管也可能同步从 0 跳到额定水量。Type655、Type996、Type508d 都在同一个时间步内互相反馈，收敛失败就很常见。

## 1.3 Type655 供水设定仍未显式连接

当前 Type655：

```text
Rated Capacity = 756000 kJ/h = 210 kW
Set Point Temperature = 未连接
初值 = 7 C
```

如果希望模型更稳定，建议不要让 Type655 的设定温度只靠初始值。应在 Equation 中显式给：

```text
T_chws_set = 8.0
```

并连接到 Type655 第 3 输入：

```text
Input 3 Set Point Temperature = T_chws_set
```

在除湿盘管加入后，固定 7 C 对除湿有利，但对收敛和室温控制都更硬。建议先用 `8.0 C` 或 `8.5 C` 排查稳定性，确认无 Message 441 后再逐步降低。

## 2. Message 441 的解决步骤

## 2.1 第一优先级：把 Type508d 的控制输入显式连接

在 `Equa-3` 中新增：

```text
W_oa_want = 0.0095
```

Type508d 修改：

| 输入 | 当前 | 建议 |
|---|---|---|
| Input 2 Fluid Flowrate | `m_oa_coil` | 保留，但建议先降到 2500-3000 kg/h 调试 |
| Input 10 Setpoint: Outlet Air Humidity Ratio | 未连接，初值 `0.0095` | 显式连接 `W_oa_want` |

## 2.2 第二优先级：不要让新风盘管水量一步跳到 4000 kg/h

当前：

```text
m_oa_coil = [38,1]*4000
```

建议先改成保守值：

```text
m_oa_coil = [38,1]*2500
```

如果湿度仍偏高，再逐步改：

```text
m_oa_coil = [38,1]*3000
m_oa_coil = [38,1]*3500
m_oa_coil = [38,1]*4000
```

不要一开始就用 4000 kg/h。原因是 Type508d 是含湿量控制，水量过大、供水 7 C、含湿量目标较低时，它的内部迭代会变得很强。

如果 TRNSYS 里方便做平滑开机，可以用 15-30 min 的 ramp，而不是阶跃。概念上是：

```text
m_oa_coil = 2500 * work_ramp
```

其中 `work_ramp` 从 0 缓慢升到 1，而不是 8:00 瞬间跳变。

## 2.3 第三优先级：减弱冷水回路代数反馈

当前回水温度：

```text
T_return_floor =
([30,2]*[30,1]+[35,1]*[35,2]+[36,2]*[36,1]+[37,1]*[37,2]+[43,2]*[43,1])
/ max(0.01,[25,2])
```

这里有两个问题：

1. 分子用的是各末端出口水温和流量。
2. 分母用的是 `[25,2]`，即 Type655 输出流量。

在迭代过程中，`[25,2]` 自身又由 `m_chiller` 决定，`m_chiller` 又由末端水量决定。这种写法容易加重收敛压力。

建议改成更直接的形式：

```text
T_return_floor =
([30,2]*[30,1]+[35,2]*[35,1]+[36,2]*[36,1]+[37,2]*[37,1]+[43,2]*[43,1])
/ max(0.01, m_load)
```

也就是分母用：

```text
m_load = m_bgs + m_hys + m_cs + m_zl + m_oa
```

不要用 `[25,2]` 作回水混合分母。这样更符合“末端实际回水混合”的物理意义，也更利于收敛。

## 2.4 第四优先级：Type508d 先不要追求过低含湿量

你现在给：

```text
W_oa_want = 0.0095 kg/kg
```

这个值接近 26 C、60%RH 的室内含湿量目标，对“送入房间空气”可以理解。但对“新风盘管出口”来说，若室外湿度很高且水量、供水温度不足，Type508d 会努力求解一个较难达到的状态。

建议调试顺序：

```text
第一轮：W_oa_want = 0.0105
第二轮：W_oa_want = 0.0100
第三轮：W_oa_want = 0.0095
```

如果 `W_oa_want = 0.0105` 没有 Message 441，而 `0.0095` 有，说明不是连线错误，而是除湿目标过强或水量/供水温度组合导致迭代困难。

## 2.5 第五优先级：检查 Type146 新风机质量流量

当前 Type146：

```text
Rated Volumetric Flow Rate = 1200 L/s
Rated Power = 7400 kJ/h = 2.06 kW
Input 4 Air Flow Rate = 未连接
初值 = 2000
```

Type508d 的空气流量来自 Type146 输出 `[31,4]`。如果 Type146 的空气流量输入未连接，空气侧流量链也不够清晰。建议显式给：

```text
m_oa_air = 5184*[38,1]
```

换算依据：

```text
1200 L/s = 1.2 m3/s
空气密度约 1.2 kg/m3
质量流量 = 1.2*1.2*3600 = 5184 kg/h
```

连接：

```text
Type146 Input 4 Air Flow Rate = m_oa_air
```

这样 Type508d 的空气侧和水侧都明确，收敛会更可靠。

## 3. 会议室 hys 末端上调 10% 的完整同步修改

你希望会议室偏热最明显时，优先略增 hys 末端水量或容量。这里建议不要只改 `m_hys`，因为 Type996 的性能图谱使用：

```text
实际水量 / 额定水量
实际风量 / 额定风量
额定总冷量
额定显冷量
额定风机功率
```

如果只把 Equation 中的 `m_hys` 增加 10%，但 Type996 额定液体流量仍是旧值，会让模型进入 `Flow_Fluid / Flow_Fluid_Rated = 1.1` 的状态，容易触碰性能图谱边界，也不符合“重新选型”的含义。

因此，hys 上调 10% 应同步改以下项目。

## 3.1 Type996 hys 参数修改表

当前会议室 hys：

```text
Rated Volumetric Air Flowrate = 2567 L/s
Rated Liquid Flowrate = 7940 kg/h
Rated Total Cooling Capacity = 166320 kJ/h = 46.2 kW
Rated Sensible Cooling Capacity = 124740 kJ/h = 34.65 kW
Rated Fan Power = 5100 kJ/h = 1.42 kW
```

上调 10% 后建议：

| 参数 | 当前值 | 上调 10% 后 |
|---|---:|---:|
| Rated Volumetric Air Flowrate | `2567 L/s` | `2824 L/s` |
| Rated Liquid Flowrate | `7940 kg/h` | `8734 kg/h` |
| Rated Total Cooling Capacity | `166320 kJ/h = 46.2 kW` | `182952 kJ/h = 50.82 kW` |
| Rated Sensible Cooling Capacity | `124740 kJ/h` | `137214 kJ/h` |
| Rated Fan Power | `5100 kJ/h = 1.42 kW` | `5600-6800 kJ/h = 1.56-1.89 kW` |

风机功率有两种取法：

- 若按相似末端、单位风量功率近似不变，取 `5600 kJ/h`。
- 若按同一风机管网、风量提高导致风机功率近似三次方增长，取 `6800 kJ/h`。

对你的模型，建议先取中间偏保守值：

```text
Rated Fan Power hys = 6000 kJ/h
```

## 3.2 Equa-3 必须同步修改

当前：

```text
m_hys = 7940*cool_hys
```

建议改为：

```text
m_hys = 8734*cool_hys
```

同时总水量基准要更新。当前：

```text
m_min = 0.3*34370
```

因为 hys 水量增加：

```text
新增水量 = 8734 - 7940 = 794 kg/h
新总末端额定水量 = 34370 + 794 = 35164 kg/h
```

所以建议：

```text
m_min = 0.3*35164
```

`m_load` 不用改公式，但会自动随 `m_hys` 增加：

```text
m_load = m_bgs + m_hys + m_cs + m_zl + m_oa
```

## 3.3 Type655 是否需要同步加大

当前 Type655：

```text
Rated Capacity = 756000 kJ/h = 210 kW
```

当前 Type996 合计约 200 kW。hys 上调 10% 后，Type996 合计变为：

```text
200 kW + 4.62 kW = 204.62 kW
```

Type655 仍为 210 kW，余量约：

```text
210 - 204.62 = 5.38 kW
```

结论：**Type655 额定容量可以暂时不改**。如果你还要考虑 Type508d 新风除湿盘管负荷由同一台冷水机承担，210 kW 可能偏紧。更稳妥的设置是：

```text
Type655 Rated Capacity = 792000 kJ/h = 220 kW
```

建议：

- 若当前目标是先稳定收敛：Type655 暂时保持 `210 kW`。
- 若后续新风除湿盘管确实持续工作，且主机 PLR 长时间接近 1：把 Type655 提到 `220 kW`。

## 3.4 S1 总能耗 Equation 要不要改

当前：

```text
P_ALL_S1 = ([25,3]+[30,11]+[35,11]+[36,11]+[37,11]+[31,6])/3600
```

这个公式本身不需要改，因为它引用的是各模块输出功率。  

但如果你修改了 hys 的 `Rated Fan Power`，`[35,11]` 会随之改变，所以能耗会自动更新。

注意：Type508d 没有单独电功率输出。它的冷量由 Type655 供冷承担，不能把 Type508d 的 `Output 8` 当作电功率加入 `P_ALL_S1`。Type508d 的：

```text
Output 8 = Q_Total
Output 9 = Q_Fluid
```

是换热量，不是电功率。

## 4. 各模块功率参数校核

## 4.1 Type655 风冷冷水机组

当前：

```text
Rated Capacity = 756000 kJ/h = 210 kW
COP = 3.2
```

满负荷输入功率约：

```text
210 / 3.2 = 65.6 kW
```

对常规风冷冷水机组，COP 3.2 是可以接受的保守值。上海夏季风冷机组在高温工况下 COP 取 3.0-3.4 比较合理。  

建议：

```text
COP = 3.2 保持不变
Rated Capacity = 210 kW 暂时保持
```

若 hys 上调后且新风除湿盘管持续工作，建议再试：

```text
Rated Capacity = 220 kW
COP = 3.2
```

## 4.2 Type996 风机盘管风机功率

当前 Type996 风机功率：

| 模块 | 风量 | 当前风机功率 | 折算功率密度 |
|---|---:|---:|---:|
| bgs | 5167 L/s | 10200 kJ/h = 2.83 kW | 0.55 W/(L/s) |
| hys | 2567 L/s | 5100 kJ/h = 1.42 kW | 0.55 W/(L/s) |
| cs | 1233 L/s | 2440 kJ/h = 0.68 kW | 0.55 W/(L/s) |
| zl | 2144 L/s | 4250 kJ/h = 1.18 kW | 0.55 W/(L/s) |

这组参数比你最早的模型合理很多。最早模型中 bgs 风机 `10.22 kW` 偏大，而 hys/cs/zl 只有 `0.16 kW` 明显偏小。现在四个区按同一功率密度校核，逻辑一致。

如果 hys 风量上调 10%，建议：

```text
hys Rated Fan Power = 6000 kJ/h
```

其他三区暂时不改。

## 4.3 Type146 新风机功率

当前：

```text
Rated Volumetric Flow Rate = 1200 L/s
Rated Power = 7400 kJ/h = 2.06 kW
```

折算：

```text
2.06 kW / 1200 L/s = 1.72 W/(L/s)
```

这个值对带过滤、盘管、管道阻力的新风机是偏高但可接受的。若你的新风系统阻力不大，可以改为：

```text
Rated Power = 5000-6500 kJ/h = 1.39-1.81 kW
```

但当前更重要的问题是：Type146 的第 4 输入空气流量仍未显式连接。建议先连接 `m_oa_air`，功率先不急着改。

## 4.4 Type508d 新风盘管功率

Type508d 是换热盘管，不是电力设备。它没有“压缩机功率”。它的冷量最终由 Type655 承担。

应输出并检查：

```text
[43,3]  出风温度
[43,4]  出风含湿量
[43,5]  出风相对湿度
[43,8]  总冷量 Q_Total
[43,9]  水侧换热量 Q_Fluid
[43,11] 冷凝水量 Flow_Condensate
[43,17] 内部迭代次数 Iters_Tot
```

尤其建议把 `[43,17]` 输出到 `测试.xls`。如果 Message 441 附近 `[43,17]` 明显升高，说明收敛失败主要来自 Type508d 内部求解。

## 5. 推荐修改清单

## 5.1 为解决 Message 441

| 位置 | 当前 | 建议 |
|---|---|---|
| Equa-3 | 无显式 `W_oa_want` | 新增 `W_oa_want = 0.0105`，稳定后再降到 `0.0100`、`0.0095` |
| Type508d Input 10 | 未连接，初值 `0.0095` | 连接 `W_oa_want` |
| Equa-3 `m_oa_coil` | `[38,1]*4000` | 先改为 `[38,1]*2500`，稳定后逐步增加 |
| Type655 Input 3 | 未连接，初值 `7 C` | 连接 `T_chws_set`，先用 `8.0 C` 或 `8.5 C` |
| Equa-3 `T_return_floor` | 分母 `max(0.01,[25,2])` | 建议改为 `max(0.01,m_load)` |
| Type146 Input 4 | 未连接 | 连接 `m_oa_air = 5184*[38,1]` |

建议先用这一组排查：

```text
T_chws_set = 8.0
W_oa_want = 0.0105
m_oa_coil = [38,1]*2500
m_oa_air = [38,1]*5184
```

如果没有 Message 441，再逐步加强除湿：

```text
W_oa_want = 0.0100
m_oa_coil = [38,1]*3000
```

最后再试：

```text
W_oa_want = 0.0095
m_oa_coil = [38,1]*3500~4000
```

## 5.2 为解决会议室偏热

| 位置 | 当前 | 建议 |
|---|---:|---:|
| Type996 hys Rated Air Flowrate | `2567` | `2824` |
| Type996 hys Rated Liquid Flowrate | `7940` | `8734` |
| Type996 hys Rated Total Cooling Capacity | `166320` | `182952` |
| Type996 hys Rated Sensible Cooling Capacity | `124740` | `137214` |
| Type996 hys Rated Fan Power | `5100` | `6000` |
| Equa-3 `m_hys` | `7940*cool_hys` | `8734*cool_hys` |
| Equa-3 `m_min` | `0.3*34370` | `0.3*35164` |
| Type655 Rated Capacity | `756000` | 暂时不改；必要时改 `792000` |

## 6. 修改后验证方式

每次只改一组，不要一次全部改，否则难以定位问题。

## 6.1 收敛验证

看 `Untitled_imported.log`：

```text
是否仍出现 Message 441
是否仍列出 UNITS: 25 30 35 36 37 43
Type2 controller stuck 是否减少
Type996 performance map warning 是否增加
```

如果 Message 441 消失，说明 Type508d 与冷水回路耦合已基本稳定。

## 6.2 温度验证

工作日 8-22 点统计：

```text
TAIR_S_hys1 平均值
TAIR_S_hys1 > 26.5 C 的占比
TAIR_S_hys1 > 28 C 的占比
cool_hys 开启率
```

hys 上调 10% 后，合理期望是：

```text
会议室平均温度下降约 0.2-0.5 C
>26.5 C 占比明显下降
>28 C 占比接近 0
```

## 6.3 湿度验证

至少输出：

```text
办公室 RH
会议室 RH
Type508d 出风含湿量 [43,4]
Type508d 冷凝水量 [43,11]
Type508d 总冷量 [43,8]
Type508d 迭代次数 [43,17]
```

判断：

- 室内 RH 目标建议先看 `50-70%`，再追求 `55-65%`。
- 如果 RH 仍高但 Message 441 消失，再逐步降低 `W_oa_want` 或增加 `m_oa_coil`。
- 如果 RH 降了但室温过低，说明新风盘管除湿造成过冷，需要提高 `T_chws_set` 或减小新风盘管水量。

## 7. 遗漏检查

本次已覆盖以下同步点：

- Type508d 第 2 输入水流量：已检查，当前接 `m_oa_coil`。
- Type508d 第 10 输入含湿量设定：当前仍未显式连接，建议接 `W_oa_want`。
- Message 441 涉及的 25/30/35/36/37/43：已按冷水回路耦合解释。
- Type655 供水温度设定：当前未连接，建议接 `T_chws_set`。
- `T_return_floor` 混合公式：建议分母改用 `m_load`，减弱迭代耦合。
- Type146 新风机空气流量：当前未连接，建议接 `m_oa_air`。
- 会议室 hys 上调 10%：已给出容量、水量、风量、显冷量、风机功率、Equa-3、m_min 的同步修改。
- Type655 容量是否同步：已判断 210 kW 暂可不改，必要时改 220 kW。
- 功率校核：已覆盖 Type655、Type996、Type146、Type508d。
- 总能耗公式：`P_ALL_S1` 公式可保留，不应把 Type508d 冷量当电功率重复加入。
