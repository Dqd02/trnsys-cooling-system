"""
净负荷比例（NLF）每日最高比例时间窗口分析
===========================================
对 15min 级（96 点/天）中国的风光发电量占比总负荷的比例（净负荷比例）数据做每日分析：
  1. 找到每天净负荷比例的 75% 分位数（即最高的 25%）
  2. 将高于该分位数的时段标记为 1（高净负荷比例窗口），其余为 0
  3. 连续性修正：孤立 1 变 0，孤立 0 变 1
  4. 验证每日分析的正确性

输入：NLF/ 下的三个 CSV 文件
输出：每个文件对应的 *_labeled.csv 和 *_window_stats.csv
"""

import pandas as pd
import numpy as np
import os

# ============================================================
# 配置区 —— 修改百分位数做敏感性分析
# ============================================================
PERCENTILE_TOP = 25  # <<<=== 关键参数：选最高的前 25%
                      #         改为 30 则选最高的前 30%，改为 10 则选最高的前 10%
# ============================================================

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = ['NLF_2025.csv', 'NLF_40th.csv', 'NLF_60th.csv']
POINTS_PER_DAY = 96
TOTAL_EXPECTED = 35041     # 有效数据行数（含 1 行初始值）


def load_file(filename):
    """
    加载 NLF 文件。兼容多种格式和 GBK 编码。
    """
    filepath = os.path.join(INPUT_DIR, filename)

    # 先尝试 GBK 编码读取（NLF_60th 使用 GBK）
    for encoding in ['gbk', 'utf-8']:
        try:
            raw = pd.read_csv(filepath, header=None, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise ValueError(f"无法解码 {filename}")

    # 两列格式 [序号, 数值]
    if raw.shape[1] >= 2:
        try:
            vals = pd.to_numeric(raw.iloc[:, 1], errors='coerce')
            if vals.notna().sum() >= 35000:
                values = vals.values
                print(f"  格式: 两列(序号, 数值) 编码:{encoding}")
                validate(filename, values)
                return values
        except:
            pass

    # 单列数值格式（跳过非数值行如文字表头）
    flat = pd.to_numeric(raw.iloc[:, 0], errors='coerce')
    values = flat.dropna().values
    print(f"  格式: 单列数值（跳过 {len(raw) - len(values)} 行非数值）编码:{encoding}")
    validate(filename, values)
    return values


def validate(filename, values):
    """验证数据完整性"""
    n = len(values)
    assert n == TOTAL_EXPECTED, \
        f"{filename}: 期望 {TOTAL_EXPECTED} 行数值，实际 {n} 行"
    print(f"  [{filename}] 总行数: {n}, "
          f"范围: {values.min():.5f} ~ {values.max():.5f}, "
          f"均值: {values.mean():.5f}")


def daily_labeling_high(values, percentile_top):
    """
    逐日标记高净负荷比例窗口。
    取当天最高的 percentile_top% 时段标为 1，其余为 0。
    第一行（索引 0）是初始值，标为 0。
    """
    n = len(values)
    labels = np.zeros(n, dtype=int)
    total_days = (n - 1) // POINTS_PER_DAY  # 365 天

    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_data = values[start:end]

        threshold = np.percentile(day_data, 100 - percentile_top)
        labels[start:end] = (day_data > threshold).astype(int)

    return labels, total_days


def continuity_fix(labels):
    fixed = labels.copy()
    n = len(fixed)
    for i in range(1, n - 1):
        if fixed[i] == 1 and fixed[i-1] == 0 and fixed[i+1] == 0:
            fixed[i] = 0
        elif fixed[i] == 0 and fixed[i-1] == 1 and fixed[i+1] == 1:
            fixed[i] = 1
    return fixed


def compute_daily_stats(values, labels, total_days):
    daily_stats = []
    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_val = values[start:end]
        day_label = labels[start:end]
        threshold = np.percentile(day_val, 100 - PERCENTILE_TOP)
        label_count = day_label.sum()
        label_pct = label_count / POINTS_PER_DAY * 100
        daily_stats.append({
            'day': day + 1,
            'threshold': threshold,
            'high_ratio_count': label_count,
            'high_ratio_pct': round(label_pct, 2)
        })
    return pd.DataFrame(daily_stats)


def process_file(filename):
    print(f"\n{'='*60}")
    print(f"处理文件: {filename}")
    print(f"{'='*60}")

    values = load_file(filename)

    labels, total_days = daily_labeling_high(values, PERCENTILE_TOP)

    # 每日标记比例验证
    daily_pcts = []
    for day in range(total_days):
        start = 1 + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        pct = labels[start:end].sum() / POINTS_PER_DAY * 100
        daily_pcts.append(pct)
    daily_pcts = np.array(daily_pcts)
    print(f"  每日标记比例: {daily_pcts.min():.1f}% ~ {daily_pcts.max():.1f}%, "
          f"均值 {daily_pcts.mean():.1f}%")

    labels_fixed = continuity_fix(labels)
    changes = (labels != labels_fixed).sum()
    print(f"  连续性修正改变点数: {changes}")

    # 输出标记文件
    output_labeled = filename.replace('.csv', '_labeled.csv')
    output_df = pd.DataFrame({
        'value': values,
        'label_raw': labels,
        'label': labels_fixed
    })
    output_path = os.path.join(INPUT_DIR, output_labeled)
    output_df.to_csv(output_path, index=False, header=False)
    print(f"  标记文件输出: {output_labeled}")

    # 输出统计
    stats_df = compute_daily_stats(values, labels_fixed, total_days)
    output_stats = filename.replace('.csv', '_window_stats.csv')
    stats_path = os.path.join(INPUT_DIR, output_stats)
    stats_df.to_csv(stats_path, index=False)
    print(f"  统计文件输出: {output_stats}")
    print(f"  每日阈值范围: {stats_df['threshold'].min():.5f} ~ "
          f"{stats_df['threshold'].max():.5f}")
    print(f"  每日高比例窗口均值: {stats_df['high_ratio_count'].mean():.1f} 个/天 "
          f"({stats_df['high_ratio_pct'].mean():.1f}%)")

    avg_pct = stats_df['high_ratio_pct'].mean()
    assert abs(avg_pct - PERCENTILE_TOP) < 5, \
        f"标记比例异常: {avg_pct:.1f}% (期望 {PERCENTILE_TOP}%)"
    assert len(labels_fixed) == TOTAL_EXPECTED
    assert labels_fixed[0] == 0

    return output_df, stats_df


def main():
    print("=" * 60)
    print(f"净负荷比例 (NLF) 每日高比例窗口分析")
    print(f"选择最高的前 {PERCENTILE_TOP}% 时段作为高净负荷比例窗口")
    print(f"数据: {POINTS_PER_DAY} 点/天, 共 {TOTAL_EXPECTED} 行")
    print("=" * 60)

    for fname in FILES:
        process_file(fname)

    print(f"\n{'='*60}")
    print("全部完成！")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
