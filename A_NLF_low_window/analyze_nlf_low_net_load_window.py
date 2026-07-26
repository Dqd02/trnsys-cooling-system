# -*- coding: utf-8 -*-
"""
净负荷（NLF）每日低净负荷时间窗口分析
=====================================
对 15min 级（96 点/天）中国净负荷数据做每日分析：
  1. 对每天 96 个点按净负荷数值升序排序，取最低的 25% 时段
     （即每天精确选出 24 个最低净负荷的时间点）；
  2. 选出的标记为 1（干净窗口），其余为 0；
  3. 连续性修正：孤立 1 变 0，孤立 0 变 1；
  4. 验证每日分析、输出长度和时间顺序。

方法选择说明（重要）：
  ═══════════════════════════════════════════════════════════════
  本脚本采用 argsort 排序法（每天精确取最低 N 个点），而非
  np.percentile 阈值法（data < P25）。原因：NLF 数据中存在
  大量 0 值（NLF_60TH 中 0 值占 21.8%），若用 data < P25，
  当 P25 = 0 时 data < 0 为 False，导致每天选出的窗口远低于
  25%（如 NLF_60TH 仅 16%），这与"每天选出最低 25% 时段"
  的工程目标不一致。

  | 方法          | 每天标记比例 | 适用场景                |
  |--------------|-------------|------------------------|
  | argsort 法   | 严格 ≈ 25%  | 工程调度、需要稳定窗口数 |
  | percentile 法 | 可能有偏    | 统计分析、严格百分位含义 |

  如需改为 percentile 法做敏感性对比，参见函数 daily_labeling_low()
  中的注释代码。
  ═══════════════════════════════════════════════════════════════

输入：NLF/ 下的三个 *_new.csv 文件（单列净负荷正值，35041 行）
输出：每个文件对应的 *_labeled.csv 和 *_window_stats.csv

修改记录：
  - 2026-06-29: 初版，采用 argsort 每天精确取最低 25% 时段
"""

import os
import numpy as np
import pandas as pd

# ============================================================
# 配置区 —— 修改百分位数做敏感性分析
# ============================================================
PERCENTILE_LOW = 25  # <<<=== 关键参数：选每天净负荷最低的 25%
                     #         改为 30 则每天选最低的 29 个点（30%×96=28.8→29）
                     #         改为 60 则每天选最低的 58 个点（60%×96=57.6→58）
# ============================================================

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = ["NLF_2025_new.csv", "NLF_40TH_new.csv", "NLF_60TH_new.csv"]
POINTS_PER_DAY = 96
TOTAL_EXPECTED = 35041


def load_file(filename):
    """读取单列净负荷 CSV，兼容 UTF-8/GBK 编码与潜在非数值行。"""
    path = os.path.join(INPUT_DIR, filename)
    last_error = None

    for encoding in ("utf-8", "gbk"):
        try:
            raw = pd.read_csv(path, header=None, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError(f"无法解码 {filename}") from last_error

    if raw.shape[1] >= 2:
        values = pd.to_numeric(raw.iloc[:, 1], errors="coerce").dropna().to_numpy()
        data_format = "两列格式，取第2列数值"
    else:
        values = pd.to_numeric(raw.iloc[:, 0], errors="coerce").dropna().to_numpy()
        data_format = "单列数值"

    print(f"  格式: {data_format}，编码: {encoding}")
    validate(filename, values)
    return values


def validate(filename, values):
    """验证有效数据长度。"""
    assert len(values) == TOTAL_EXPECTED, (
        f"{filename}: 期望 {TOTAL_EXPECTED} 行数值，实际 {len(values)} 行"
    )
    print(
        f"  [{filename}] 总行数: {len(values)}, "
        f"范围: {values.min():.3f} ~ {values.max():.3f}, "
        f"均值: {values.mean():.3f}"
    )


def daily_labeling_low(values, percentile_low):
    """
    逐日标记低净负荷窗口。

    方法：每天按数值升序排序，取最低的 round(96 * pct / 100) 个。
    第一行（索引 0）是初始值，标记为 0。

    敏感性分析：修改 PERCENTILE_LOW 即可，每天选点数为
      round(96 * PERCENTILE_LOW / 100)

    如需改为 percentile 阈值法（低于 P25 标 1），用下面的代码替换：
    ────────────────────────────────────────────────────────────
    threshold = np.percentile(day_data, percentile_low)
    labels[start:end] = (day_data < threshold).astype(int)
    ────────────────────────────────────────────────────────────
    但注意当数据中有大量重复极值时，此法可能选不够 pct%。
    """
    n = len(values)
    labels = np.zeros(n, dtype=int)
    total_days = (n - 1) // POINTS_PER_DAY
    select_count = round(POINTS_PER_DAY * percentile_low / 100)

    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_data = values[start:end]

        # 找到最低的 select_count 个位置的索引
        lowest_positions = np.argsort(day_data, kind="stable")[:select_count]
        labels[start + lowest_positions] = 1

    return labels, total_days


def continuity_fix(labels):
    """孤立 1 变 0，孤立 0 变 1。"""
    fixed = labels.copy()
    for i in range(1, len(fixed) - 1):
        if fixed[i] == 1 and fixed[i - 1] == 0 and fixed[i + 1] == 0:
            fixed[i] = 0
        elif fixed[i] == 0 and fixed[i - 1] == 1 and fixed[i + 1] == 1:
            fixed[i] = 1
    return fixed


def compute_daily_stats(values, labels, total_days, percentile_low):
    """生成每日阈值与窗口数量统计。"""
    rows = []
    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_val = values[start:end]
        day_label = labels[start:end]

        threshold = np.percentile(day_val, percentile_low)
        low_count = int(day_label.sum())
        rows.append(
            {
                "day": day + 1,
                "P" + str(percentile_low) + "_threshold": threshold,
                "low_net_load_count": low_count,
                "low_net_load_pct": round(low_count / POINTS_PER_DAY * 100, 2),
            }
        )

    return pd.DataFrame(rows)


def assert_no_isolated_points(labels):
    """验证修正后不存在 0-1-0 或 1-0-1 模式。"""
    isolated_one = []
    isolated_zero = []
    for i in range(1, len(labels) - 1):
        if labels[i - 1] == 0 and labels[i] == 1 and labels[i + 1] == 0:
            isolated_one.append(i)
        if labels[i - 1] == 1 and labels[i] == 0 and labels[i + 1] == 1:
            isolated_zero.append(i)

    assert not isolated_one, f"仍存在孤立 1: {isolated_one[:5]}"
    assert not isolated_zero, f"仍存在孤立 0: {isolated_zero[:5]}"


def process_file(filename):
    print(f"\n{'=' * 60}")
    print(f"处理文件: {filename}")
    print(f"{'=' * 60}")

    values = load_file(filename)
    labels_raw, total_days = daily_labeling_low(values, PERCENTILE_LOW)

    # 修正前每日统计
    daily_pcts = []
    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        daily_pcts.append(labels_raw[start:end].sum() / POINTS_PER_DAY * 100)
    daily_pcts = np.array(daily_pcts)
    print(
        f"  修正前每日标记比例: {daily_pcts.min():.1f}% ~ "
        f"{daily_pcts.max():.1f}%，均值 {daily_pcts.mean():.1f}%"
    )

    labels_fixed = continuity_fix(labels_raw)
    changes = int((labels_raw != labels_fixed).sum())
    print(f"  连续性修正改变点数: {changes}")

    # 输出标记文件（3 列，无表头）
    output_df = pd.DataFrame(
        {"value": values, "label_raw": labels_raw, "label": labels_fixed}
    )
    labeled_name = filename.replace(".csv", "_labeled.csv")
    output_df.to_csv(os.path.join(INPUT_DIR, labeled_name), index=False, header=False)
    print(f"  标记文件输出: {labeled_name}")

    # 输出统计文件（有表头）
    stats_df = compute_daily_stats(values, labels_fixed, total_days, PERCENTILE_LOW)
    stats_name = filename.replace(".csv", "_window_stats.csv")
    stats_df.to_csv(os.path.join(INPUT_DIR, stats_name), index=False)
    print(f"  统计文件输出: {stats_name}")
    print(
        f"  每日 P{PERCENTILE_LOW} 阈值范围: "
        f"{stats_df.iloc[:, 1].min():.3f} ~ {stats_df.iloc[:, 1].max():.3f}"
    )
    print(
        f"  每日低净负荷窗口均值: "
        f"{stats_df['low_net_load_count'].mean():.1f} 个/天 "
        f"({stats_df['low_net_load_pct'].mean():.1f}%)"
    )

    # 最终断言
    assert len(output_df) == TOTAL_EXPECTED
    assert labels_fixed[0] == 0
    assert total_days == 365
    assert_no_isolated_points(labels_fixed)

    return output_df, stats_df


def main():
    print("=" * 60)
    print("净负荷 (NLF) 每日低净负荷窗口分析")
    print(f"方法: 每天按数值升序取最低的 {PERCENTILE_LOW}% 时段标记为 1")
    print(f"数据: {POINTS_PER_DAY} 点/天，共 {TOTAL_EXPECTED} 行")
    print("=" * 60)

    for filename in FILES:
        process_file(filename)

    print(f"\n{'=' * 60}")
    print("全部完成！")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
