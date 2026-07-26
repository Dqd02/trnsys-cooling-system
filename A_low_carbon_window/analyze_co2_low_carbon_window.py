"""
电力碳排放因子每日低碳窗口分析
=================================
对 15min 级（96 点/天）电力碳排放因子数据做每日分析：
  1. 找到每天碳因子的 25% 分位数
  2. 将低于该分位数的时段标记为 1（低碳窗口），其余为 0
  3. 连续性修正：孤立 1 变 0，孤立 0 变 1
  4. 验证每日分析的正确性

输入：time_CO2/ 下的三个 CSV 文件（单列，35041 行）
输出：每个文件对应的 *_labeled.csv 和 *_window_stats.csv
"""

import pandas as pd
import numpy as np
import os

# ============================================================
# 配置区 —— 修改百分位数做敏感性分析
# ============================================================
PERCENTILE = 25  # <<<=== 关键参数：默认 25%，修改为 30/60 等做敏感性分析
# ============================================================

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = ['2025_g_kw.csv', '40th_g_kwh.csv', '60th_g_kwh.csv']
POINTS_PER_DAY = 96       # 15min 间隔，24h = 96
INITIAL_ROW = 1            # 第一行是初始值
TOTAL_EXPECTED = 35041     # 1 + 8760*4 = 35041


def load_and_validate(filename):
    filepath = os.path.join(INPUT_DIR, filename)
    df = pd.read_csv(filepath, header=None, names=['value'])
    
    assert len(df) == TOTAL_EXPECTED, \
        f"{filename}: 期望 {TOTAL_EXPECTED} 行，实际 {len(df)} 行"
    
    print(f"  [{filename}] 总行数: {len(df)}, "
          f"范围: {df['value'].min():.2f} ~ {df['value'].max():.2f}, "
          f"均值: {df['value'].mean():.2f}")
    return df


def daily_labeling(df, percentile):
    values = df['value'].values
    n = len(values)
    labels = np.zeros(n, dtype=int)
    
    labels[0] = 0
    
    total_days = (n - INITIAL_ROW) // POINTS_PER_DAY
    
    for day in range(total_days):
        start = INITIAL_ROW + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_data = values[start:end]
        
        threshold = np.percentile(day_data, percentile)
        labels[start:end] = (day_data < threshold).astype(int)
    
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
        start = INITIAL_ROW + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        day_val = values[start:end]
        day_label = labels[start:end]
        
        threshold = np.percentile(day_val, PERCENTILE)
        label_count = day_label.sum()
        label_pct = label_count / POINTS_PER_DAY * 100
        
        daily_stats.append({
            'day': day + 1,
            'threshold': threshold,
            'low_carbon_count': label_count,
            'low_carbon_pct': round(label_pct, 2)
        })
    
    return pd.DataFrame(daily_stats)


def process_file(filename):
    print(f"\n{'='*60}")
    print(f"处理文件: {filename}")
    print(f"{'='*60}")
    
    df = load_and_validate(filename)
    values = df['value'].values
    
    labels, total_days = daily_labeling(df, PERCENTILE)
    df['label_raw'] = labels
    
    daily_pcts = []
    for day in range(total_days):
        start = INITIAL_ROW + day * POINTS_PER_DAY
        end = start + POINTS_PER_DAY
        pct = labels[start:end].sum() / POINTS_PER_DAY * 100
        daily_pcts.append(pct)
    daily_pcts = np.array(daily_pcts)
    print(f"  每日标记比例: {daily_pcts.min():.1f}% ~ {daily_pcts.max():.1f}%, "
          f"均值 {daily_pcts.mean():.1f}%")
    
    labels_fixed = continuity_fix(labels)
    df['label'] = labels_fixed
    
    changes = (labels != labels_fixed).sum()
    print(f"  连续性修正改变点数: {changes}")
    
    output_labeled = filename.replace('.csv', '_labeled.csv')
    output_path = os.path.join(INPUT_DIR, output_labeled)
    df.to_csv(output_path, index=False, header=False)
    print(f"  标记文件输出: {output_labeled}")
    
    stats_df = compute_daily_stats(values, labels_fixed, total_days)
    output_stats = filename.replace('.csv', '_window_stats.csv')
    stats_path = os.path.join(INPUT_DIR, output_stats)
    stats_df.to_csv(stats_path, index=False)
    print(f"  统计文件输出: {output_stats}")
    print(f"  每日阈值范围: {stats_df['threshold'].min():.2f} ~ "
          f"{stats_df['threshold'].max():.2f}")
    print(f"  每日低碳窗口数量均值: {stats_df['low_carbon_count'].mean():.1f} 个/天 "
          f"({stats_df['low_carbon_pct'].mean():.1f}%)")
    
    avg_pct = stats_df['low_carbon_pct'].mean()
    assert abs(avg_pct - (100 - PERCENTILE)) < 5 or abs(avg_pct - PERCENTILE) < 5, \
        f"标记比例异常: {avg_pct:.1f}%"
    
    assert len(df) == TOTAL_EXPECTED, \
        f"输出行数 {len(df)} 与输入 {TOTAL_EXPECTED} 不匹配"
    assert df['label'].iloc[0] == 0, "初始值标记不为 0"
    
    return df, stats_df


def main():
    print("=" * 60)
    print(f"电力碳排放因子 每日低碳窗口分析")
    print(f"百分位数: P{PERCENTILE} (低于该分位数的为低碳窗口)")
    print(f"数据: {POINTS_PER_DAY} 点/天, 共 {TOTAL_EXPECTED - 1} 个有效数据点")
    print("=" * 60)
    
    for fname in FILES:
        process_file(fname)
    
    print(f"\n{'='*60}")
    print("全部完成！")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
