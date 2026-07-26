你这个界面就是对的，**这里应该新建一个“空调对房间的负增益 / 负湿量源”**。我把你截图里的每一项都拆开说。你现在先不要填 `50`，这个值只是测试常数，真正闭环时要让它变成 **Type954 输出的制冷量输入**。

---

## 1. 这个 Gain/loss Type 应该怎么理解？

你现在建的：

```text
GAIN_DX_S_bgs1
```

它不是人员得热、不是照明、不是设备，而是：

```text
分体式空调从 S_bgs1 房间空气中拿走的热量和水分
```

所以它本质上是一个**负的内部增益**：

```text
显冷量：负 convective gain
除湿量：负 absolute humidity gain
```

也就是：

```text
房间热平衡中：
人员、灯光、设备、太阳辐射 = 正增益
分体式空调制冷 = 负增益
```

---

## 2. Gain/loss Category 应该选哪个？

你这里应该选：

```text
miscellaneous
```

不要选：

```text
people
lights
electrical equipment
thermal bridge
```

原因如下：

|选项|是否适合 DX 空调负增益|原因|
|---|---|---|
|people|不适合|人员得热、得湿用|
|lights|不适合|照明得热用|
|electrical equipment|不适合|插座设备得热用|
|thermal bridge|不适合|热桥传热用|
|miscellaneous|适合|自定义热源/冷源/湿源/除湿源|

所以你截图里选 **miscellaneous** 是对的。

---

## 3. 选择 absolute gain/loss

你现在这里有两个选项：

```text
absolute gain/loss
gain/loss related to reference floor area
```

你应该选：

```text
absolute gain/loss
```

原因是 Type954 输出的是某一台空调的实际制冷量，比如：

```text
Q_sensible_c = 50000 kJ/h
```

这个值已经是整个房间/整个热区的总制冷量，不需要再乘以面积。

如果你选：

```text
gain/loss related to reference floor area
```

那 TRNBuild 会把你输入的值理解成单位面积增益，再乘以房间面积。你的 `S_bgs1` 面积如果是几百平方米，冷量会被放大几百倍，结果直接崩掉。

所以这里必须是：

```text
absolute gain/loss
```

---

## 4. Radiative 这里填多少？

你应该填：

```text
Radiative = 0 kJ/h
```

原因：分体式空调室内机主要通过送风冷却房间空气，属于**对流换热**，不是辐射冷板。

所以：

```text
Radiative = 0
```

这个你截图里已经填对了。

---

## 5. Convective 这里不要填 50，要设成输入

你截图里现在填的是：

```text
Convective = 50 kJ/h
```

这个只是一个固定正得热，不是我们要的。

我们真正要的是：

```text
Convective = INPUT
```

并且这个输入后面由 Type954 的显冷量决定：

```text
Q_DX_convective = - Q_sensible_c
```

这里注意一个非常重要的单位问题：**你这个 TRNBuild 界面显示 Convective 的单位是 kJ/h**，而 Type954 的 `Q_sensible_c` 输出也是 kJ/h，所以这里**不要除以 3.6**。

也就是说，在 Equation 里应该写：

```text
Q_DX_S_bgs1 = -[DX_S_bgs1,7]
```

而不是：

```text
Q_DX_S_bgs1 = -[DX_S_bgs1,7]/3.6
```

`/3.6` 只有在你要把 kJ/h 转成 W 时才用。但你现在这个 Gain/loss 界面本身就是 kJ/h，所以直接取负即可。

---

## 6. Convective 怎么设成 INPUT？

你看 Convective 左边有一个绿色小按钮。你需要点它。

一般流程是：

```text
点击 Convective 左侧绿色按钮
→ 选择 Input / External input / 输入变量
→ 新建或选择一个输入变量
→ 命名为 Q_DX_S_bgs1
```

不同 TRNBuild 版本界面名字可能略有差异，但你要找的核心选项就是：

```text
INPUT
```

或者：

```text
external input
```

设置完成后，Convective 这一栏不应该是固定数字 `50`，而应该显示类似：

```text
INPUT Q_DX_S_bgs1
```

或者：

```text
Q_DX_S_bgs1
```

或者 TRNBuild 自动显示某个 input 编号。

如果你的界面不能直接新建输入，那就先在 TRNBuild 的 input manager 里增加一个 input，名字叫：

```text
Q_DX_S_bgs1
```

然后再回到这个 Gain/loss Type，把 Convective 关联到这个 input。

---

## 7. Electric Power Fraction 设为 0

这里必须填：

```text
Electric Power Fraction = 0
```

你截图里已经是 0，这是对的。

原因是这个 Gain/loss 不是电器设备得热，而是空调制冷效果。分体式空调的压缩机和室外风机主要在室外侧耗电，不能作为房间内部热增益加回 Type56。

否则会出现很荒唐的能量逻辑：

```text
空调一边给房间制冷
一边又把空调电功率作为室内得热加回房间
```

这会抵消一部分冷量，结果不干净。

所以：

```text
Electric Power Fraction = 0
```

空调电耗应该在 Studio 里通过 Type954 的 power output 单独统计，不要通过 Type56 的 internal gain 统计。

---

## 8. Abs. Humidity 这里也要设成 INPUT

你现在截图里是：

```text
Abs. Humidity = 0 kg/hr
```

如果你只想先跑通显热闭环，可以暂时保持 0。

但你说要处理：

```text
显热 + 潜热
```

那么这里最终也要设成输入。

它代表：

```text
空调从房间空气中除去的水分
```

所以应该是负值：

```text
M_DX_S_bgs1 = - Flow_cond
```

Type954 的输出 21 是凝结水流量，单位是 kg/h，所以可以直接接：

```text
M_DX_S_bgs1 = -[DX_S_bgs1,21]
```

同样不需要换算。

最终 Abs. Humidity 应该关联到一个输入变量，例如：

```text
M_DX_S_bgs1
```

完整形式是：

```text
Abs. Humidity = INPUT M_DX_S_bgs1
```

---

## 9. 你这个界面最终应该设置成这样

建议最终设置如下：

```text
new gain type:
GAIN_DX_S_bgs1

Gain/loss Category:
miscellaneous

选择：
absolute gain/loss

Radiative:
0 kJ/h

Convective:
INPUT Q_DX_S_bgs1

Electric Power Fraction:
0

Abs. Humidity:
INPUT M_DX_S_bgs1
```

如果用表格表示：

|项目|设置|说明|
|---|---|---|
|Category|miscellaneous|自定义空调负增益|
|absolute / area-related|absolute gain/loss|不按面积放大|
|Radiative|0 kJ/h|分体机不是辐射冷却|
|Convective|`INPUT Q_DX_S_bgs1`|接 Type954 显冷量取负|
|Electric Power Fraction|0|空调电耗不作为室内得热|
|Abs. Humidity|`INPUT M_DX_S_bgs1`|接 Type954 凝结水量取负|

---

## 10. 在 Studio 里的 Equation 应该这样写

假设你的 Type954 单元叫：

```text
DX_S_bgs1
```

那么 Equation 里写：

```text
Q_DX_S_bgs1 = -max(0,[DX_S_bgs1,7])
M_DX_S_bgs1 = -max(0,[DX_S_bgs1,21])
P_DX_S_bgs1 = [DX_S_bgs1,13]/3600
```

解释：

```text
[DX_S_bgs1,7]
```

是 Type954 的显冷量，单位 kJ/h。

```text
[DX_S_bgs1,21]
```

是凝结水量，单位 kg/h。

```text
[DX_S_bgs1,13]
```

是空调电功率，单位 kJ/h，所以除以 3600 得到 kW。

所以真正接回 Type56 的是：

```text
Q_DX_S_bgs1    → GAIN_DX_S_bgs1 的 Convective input
M_DX_S_bgs1    → GAIN_DX_S_bgs1 的 Abs. Humidity input
```

而 `P_DX_S_bgs1` 只用于能耗统计，不接回 Type56。

---

## 11. 下一步：把这个 Gain/loss 挂到 S_bgs1 这个 airnode 上

你现在只是创建了一个 Gain/loss Type。创建完成后，还没有真正作用到房间。

下一步要做：

```text
进入 S_bgs1 airnode
→ 找到 Gains / Internal gains / Regime gains
→ 添加一个 gain
→ 选择 GAIN_DX_S_bgs1
→ multiplier 或 factor 设为 1
→ schedule 设为 always on 或 1
```

为什么 schedule 可以设为 1？

因为空调开关已经由 Type954 的 `Cooling control signal` 控制了。Type954 关机时：

```text
Q_sensible_c = 0
Flow_cond = 0
```

所以反馈给 Type56 的负增益自然就是 0，不需要在 TRNBuild 的 gain 里再加一层开关。

---

## 12. 先建议你只接显热，跑通后再接除湿

为了降低错误概率，建议你分两步做。

### 第一步：只接显热

Gain/loss 设置为：

```text
Radiative = 0
Convective = INPUT Q_DX_S_bgs1
Abs. Humidity = 0
```

Studio Equation：

```text
Q_DX_S_bgs1 = -max(0,[DX_S_bgs1,7])
```

先看 `S_bgs1` 的温度能不能被控制住。

### 第二步：再接除湿

确认温度闭环正常后，再把：

```text
Abs. Humidity = INPUT M_DX_S_bgs1
```

Studio Equation：

```text
M_DX_S_bgs1 = -max(0,[DX_S_bgs1,21])
```

这样更稳。因为湿度反馈一旦符号或单位错，很容易导致相对湿度异常、含湿量为负、psychrometric calculation 报错。

---

## 13. 最容易犯的 5 个错误

你这一步最容易出错的地方是这些：

```text
错误 1：Convective 填正值
```

空调制冷必须是负值：

```text
Q_DX_S_bgs1 = -[DX,7]
```

---

```text
错误 2：选了 related to reference floor area
```

这样会按面积放大冷量，千万别选。

---

```text
错误 3：把 Type954 电功率接到 Electric Power Fraction
```

不要这么做。电功率单独统计，不作为房间得热。

---

```text
错误 4：把 Type954 总冷量 Output 6 接回 Type56 的 Convective
```

Convective 应该接显冷量：

```text
Output 7 = Q_sensible_c
```

总冷量包含潜热，不能全部作为显热负增益。

---

```text
错误 5：Abs. Humidity 接正值
```

除湿是从空气中移除水分，所以应该是负值：

```text
M_DX_S_bgs1 = -[DX,21]
```

不是正值。

---

你现在这张界面具体应该改成：**Category 保持 miscellaneous，absolute 保持选中，Radiative=0，Convective 不填 50 而是设成外部输入 `Q_DX_S_bgs1`，Electric Power Fraction=0，Abs. Humidity 先设 0；等显热闭环跑通后，再改成外部输入 `M_DX_S_bgs1`。**