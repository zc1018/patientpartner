#!/usr/bin/env python3
"""
车厢效能评估分析脚本
分析各车厢的投入产出效率和价值分转化效果
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# 设置显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)

def load_milestone_data():
    """加载4个里程碑文件，筛选FCM-评估状态=可进车厢的需求"""
    milestone_files = [
        ('8R+OHT 里程碑节点 0202.xlsx', '0202'),
        ('8R+OHT 里程碑节点 0223.xlsx', '0223'),
        ('8R+OHT 里程碑节点 0309.xlsx', '0309'),
        ('8R+OHT 里程碑节点 0323.xlsx', '0323')
    ]

    all_requirements = []

    for file_name, milestone in milestone_files:
        try:
            df = pd.read_excel(file_name, sheet_name=0)
            df['里程碑'] = milestone

            # 筛选FCM-评估状态=可进车厢的需求
            if 'FCM-评估状态' in df.columns:
                df_valid = df[df['FCM-评估状态'] == '可进车厢'].copy()
                print(f"{file_name}: 总需求 {len(df)} 条，可进车厢 {len(df_valid)} 条")
                all_requirements.append(df_valid)
            else:
                print(f"警告: {file_name} 没有FCM-评估状态列")
        except Exception as e:
            print(f"错误读取 {file_name}: {e}")

    if all_requirements:
        return pd.concat(all_requirements, ignore_index=True)
    return pd.DataFrame()

def load_value_score_data():
    """加载价值分统计数据"""
    try:
        df = pd.read_excel('系统价值分统计.xlsx', sheet_name='全部周期')
        print(f"\n价值分统计数据: {len(df)} 条记录")
        return df
    except Exception as e:
        print(f"错误读取价值分数据: {e}")
        return pd.DataFrame()

def calculate_resource_days(df_req):
    """计算各需求的资源投入（使用BG点数作为投入指标）"""

    # 转换BG点数为数值类型
    if 'BG点数合计' in df_req.columns:
        df_req['BG点数合计'] = pd.to_numeric(df_req['BG点数合计'], errors='coerce').fillna(0)
        df_req['总投入'] = df_req['BG点数合计']
    else:
        df_req['总投入'] = 0

    # 同时计算人日（如果有的话）
    resource_cols = [
        'FCM-资源人日-RD',
        'FCM-资源人日-FE',
        'FCM-资源人日-APP',
        'FCM-资源人日-AI',
        'FCM-资源人日-DT',
        'FCM-资源人日-QA'
    ]

    for col in resource_cols:
        if col in df_req.columns:
            df_req[col] = pd.to_numeric(df_req[col], errors='coerce').fillna(0)

    df_req['总人日'] = df_req[[col for col in resource_cols if col in df_req.columns]].sum(axis=1)

    # 如果总投入为0但有总人日，使用总人日
    df_req['总投入'] = np.where(
        (df_req['总投入'] == 0) & (df_req['总人日'] > 0),
        df_req['总人日'],
        df_req['总投入']
    )

    return df_req

def normalize_carriage_name(name):
    """标准化车厢名称，移除-FC后缀"""
    if pd.isna(name):
        return name
    name = str(name).strip()
    # 移除-FC后缀
    if name.endswith('-FC'):
        name = name[:-3]
    # 映射特殊名称
    mapping = {
        '三方能力对接': '三方对接',
        '学员全旅程服务': '学员旅程',
        '督导学服务': '督导学',
        '站内营销': '营销车厢'
    }
    return mapping.get(name, name)

def analyze_carriage_efficiency(df_req, df_value):
    """分析各车厢的效能指标"""

    # 标准化车厢名称
    df_req['车厢_标准化'] = df_req['FCM-主车厢'].apply(normalize_carriage_name)

    # 1. 按车厢统计需求和投入
    carriage_stats = df_req.groupby('车厢_标准化').agg({
        '需求名称': 'count',
        '总投入': 'sum',
        '总人日': 'sum',
        '需求分类标签': lambda x: list(x.dropna().unique())
    }).reset_index()
    carriage_stats.columns = ['车厢', '需求数量', '总投入', '总人日投入', '需求分类标签']

    # 2. 计算价值分变动
    # 按车厢和系统分组计算价值分变化
    value_by_carriage = df_value.groupby(['车厢', '系统名称']).agg({
        '总分': ['first', 'last', 'mean'],
        '日期': ['min', 'max']
    }).reset_index()

    value_by_carriage.columns = ['车厢', '系统名称', '首周总分', '末周总分', '平均总分', '开始日期', '结束日期']
    value_by_carriage['价值分变动'] = value_by_carriage['末周总分'] - value_by_carriage['首周总分']

    # 按车厢汇总价值分变动
    carriage_value = value_by_carriage.groupby('车厢').agg({
        '价值分变动': 'sum',
        '系统名称': 'count'
    }).reset_index()
    carriage_value.columns = ['车厢', '总价值分变动', '系统数量']

    # 3. 合并数据
    carriage_efficiency = carriage_stats.merge(carriage_value, on='车厢', how='outer')
    carriage_efficiency = carriage_efficiency.fillna(0)

    # 4. 计算效能指标（使用总投入 - BG点数）
    carriage_efficiency['投入产出比'] = np.where(
        carriage_efficiency['总投入'] > 0,
        carriage_efficiency['总价值分变动'] / carriage_efficiency['总投入'],
        0
    )

    carriage_efficiency['单位投入价值分产出'] = np.where(
        carriage_efficiency['总投入'] > 0,
        carriage_efficiency['总价值分变动'] / carriage_efficiency['总投入'],
        0
    )

    return carriage_efficiency, value_by_carriage

def analyze_requirement_success_rate(df_req, df_value):
    """分析需求成功率（正向价值分变动的需求占比）"""

    # 获取每个需求对应的价值分变化
    # 这里假设需求与系统/车厢有关联
    req_value_analysis = []

    for _, req in df_req.iterrows():
        carriage = req['FCM-主车厢']
        normalized_carriage = normalize_carriage_name(carriage)

        # 查找该车厢的价值分变化（使用标准化后的车厢名）
        carriage_value = df_value[df_value['车厢'] == normalized_carriage]

        if not carriage_value.empty:
            # 计算该车厢的价值分变化
            first_score = carriage_value['总分'].iloc[0] if len(carriage_value) > 0 else 0
            last_score = carriage_value['总分'].iloc[-1] if len(carriage_value) > 0 else 0
            value_change = last_score - first_score

            req_value_analysis.append({
                '需求名称': req['需求名称'],
                '车厢': normalize_carriage_name(carriage),
                '总投入': req['总投入'],
                '总人日': req['总人日'],
                '需求分类标签': req.get('需求分类标签', ''),
                '价值分变动': value_change,
                '里程碑': req['里程碑']
            })

    df_req_value = pd.DataFrame(req_value_analysis)

    if df_req_value.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 标记正向价值分变动
    df_req_value['正向变动'] = df_req_value['价值分变动'] > 0

    # 按车厢统计成功率
    success_rate = df_req_value.groupby('车厢').agg({
        '正向变动': ['count', 'sum'],
        '价值分变动': 'sum',
        '总投入': 'sum',
        '总人日': 'sum'
    }).reset_index()

    success_rate.columns = ['车厢', '总需求数', '正向变动数', '总价值分变动', '总投入', '总人日投入']
    success_rate['需求成功率'] = success_rate['正向变动数'] / success_rate['总需求数'] * 100

    return success_rate, df_req_value

def extract_main_category(tag):
    """提取需求分类标签的主类别"""
    if pd.isna(tag):
        return '未分类'
    tag = str(tag).strip()

    # 提取方括号中的类别
    if '[功能开发类]' in tag:
        return '功能开发类'
    elif '[数据看板类]' in tag:
        return '数据看板类'
    elif '[优化调整类]' in tag:
        return '优化调整类'
    elif '[流程变更类]' in tag:
        return '流程变更类'
    else:
        return '其他'

def extract_priority(tag):
    """提取需求优先级"""
    if pd.isna(tag):
        return '未分类'
    tag = str(tag).strip()

    if '【重点需求】' in tag:
        return '重点需求'
    elif '【标准需求】' in tag:
        return '标准需求'
    elif '【创新需求】' in tag:
        return '创新需求'
    else:
        return '其他'

def analyze_requirement_types(df_req_value):
    """分析不同需求分类标签的价值分贡献"""

    if df_req_value.empty or '需求分类标签' not in df_req_value.columns:
        return pd.DataFrame(), pd.DataFrame()

    # 提取主类别和优先级
    df_req_value = df_req_value.copy()
    df_req_value['主类别'] = df_req_value['需求分类标签'].apply(extract_main_category)
    df_req_value['优先级'] = df_req_value['需求分类标签'].apply(extract_priority)

    # 1. 按主类别统计
    category_stats = df_req_value.groupby('主类别').agg({
        '价值分变动': ['count', 'sum', 'mean'],
        '总投入': 'sum',
        '总人日': 'sum'
    }).reset_index()
    category_stats.columns = ['需求分类', '需求数量', '总价值分变动', '平均价值分变动', '总投入', '总人日投入']
    category_stats['投入产出比'] = np.where(
        category_stats['总投入'] > 0,
        category_stats['总价值分变动'] / category_stats['总投入'],
        0
    )

    # 2. 按优先级统计
    priority_stats = df_req_value.groupby('优先级').agg({
        '价值分变动': ['count', 'sum', 'mean'],
        '总投入': 'sum',
        '总人日': 'sum'
    }).reset_index()
    priority_stats.columns = ['需求优先级', '需求数量', '总价值分变动', '平均价值分变动', '总投入', '总人日投入']
    priority_stats['投入产出比'] = np.where(
        priority_stats['总投入'] > 0,
        priority_stats['总价值分变动'] / priority_stats['总投入'],
        0
    )

    return category_stats, priority_stats

def identify_problems(carriage_efficiency, success_rate, df_req_value):
    """识别问题车厢"""

    problems = []

    # 1. 资源浪费严重的车厢（高投入低产出）
    median_input = carriage_efficiency['总投入'].median()
    median_output = carriage_efficiency['总价值分变动'].median()

    high_input_low_output = carriage_efficiency[
        (carriage_efficiency['总投入'] > median_input) &
        (carriage_efficiency['总价值分变动'] < median_output)
    ]

    for _, row in high_input_low_output.iterrows():
        problems.append({
            '车厢': row['车厢'],
            '问题类型': '资源浪费严重',
            '问题描述': f"BG点数投入{row['总投入']:.1f}点，但价值分变动仅{row['总价值分变动']:.2f}分",
            '建议': '优化需求选择，聚焦高价值需求'
        })

    # 2. 需求选择不当的车厢（低成功率）
    if not success_rate.empty:
        low_success = success_rate[success_rate['需求成功率'] < 50]
        for _, row in low_success.iterrows():
            if row['车厢'] not in [p['车厢'] for p in problems if p['问题类型'] == '资源浪费严重']:
                problems.append({
                    '车厢': row['车厢'],
                    '问题类型': '需求选择不当',
                    '问题描述': f"需求成功率仅{row['需求成功率']:.1f}%",
                    '建议': '加强需求价值评估，优先投入正向价值分需求'
                })

    # 3. 零产出车厢
    zero_output = carriage_efficiency[carriage_efficiency['总价值分变动'] == 0]
    for _, row in zero_output.iterrows():
        if row['总投入'] > 0:
            problems.append({
                '车厢': row['车厢'],
                '问题类型': '零价值产出',
                '问题描述': f"BG点数投入{row['总投入']:.1f}点，但价值分无变化",
                '建议': '复盘需求价值，调整资源分配策略'
            })

    return pd.DataFrame(problems)

def generate_report(carriage_efficiency, success_rate, category_stats, priority_stats, problems, df_req_value):
    """生成效能评估报告"""

    report = []
    report.append("# 车厢效能评估报告")
    report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**数据来源**: 4个里程碑文件 + 系统价值分统计")
    report.append(f"**分析范围**: FCM-评估状态=可进车厢的需求")
    report.append("\n---\n")

    # 1. 各车厢效能指标对比表
    report.append("## 一、各车厢效能指标对比\n")

    # 合并效能和成功率数据
    if not success_rate.empty:
        combined = carriage_efficiency.merge(success_rate[['车厢', '需求成功率']], on='车厢', how='left')
    else:
        combined = carriage_efficiency.copy()
        combined['需求成功率'] = 0

    report.append("| 车厢 | 需求数量 | 总BG点数投入 | 总价值分变动 | 投入产出比 | 需求成功率 |")
    report.append("|------|----------|--------------|--------------|------------|------------|")

    for _, row in combined.iterrows():
        report.append(f"| {row['车厢']} | {int(row['需求数量'])} | {row['总投入']:.1f} | "
                     f"{row['总价值分变动']:.2f} | {row['投入产出比']:.2f} | "
                     f"{row['需求成功率']:.1f}% |")

    # 2. 车厢效能排名
    report.append("\n## 二、车厢效能排名\n")

    # 按投入产出比排名
    report.append("### 2.1 按投入产出比排名\n")
    sorted_by_roi = combined.sort_values('投入产出比', ascending=False)

    report.append("| 排名 | 车厢 | 投入产出比 | 总价值分变动 | 总BG点数投入 |")
    report.append("|------|------|------------|--------------|--------------|")

    for i, (_, row) in enumerate(sorted_by_roi.iterrows(), 1):
        report.append(f"| {i} | {row['车厢']} | {row['投入产出比']:.2f} | "
                     f"{row['总价值分变动']:.2f} | {row['总投入']:.1f} |")

    # 按价值分转化效率排名（单位投入产出）
    report.append("\n### 2.2 按单位BG点数价值分产出排名\n")
    sorted_by_efficiency = combined.sort_values('单位投入价值分产出', ascending=False)

    report.append("| 排名 | 车厢 | 单位BG点产出 | 总价值分变动 | 总BG点数投入 |")
    report.append("|------|------|--------------|--------------|--------------|")

    for i, (_, row) in enumerate(sorted_by_efficiency.iterrows(), 1):
        report.append(f"| {i} | {row['车厢']} | {row['单位投入价值分产出']:.2f} | "
                     f"{row['总价值分变动']:.2f} | {row['总投入']:.1f} |")

    # 3. 需求类型分析
    report.append("\n## 三、需求类型效能分析\n")

    if not category_stats.empty:
        report.append("### 3.1 按需求类别分析\n")

        report.append("| 需求类别 | 需求数量 | 总BG点数投入 | 总价值分变动 | 平均价值分变动 | 投入产出比 |")
        report.append("|----------|----------|--------------|--------------|----------------|------------|")

        sorted_category = category_stats.sort_values('投入产出比', ascending=False)
        for _, row in sorted_category.iterrows():
            report.append(f"| {row['需求分类']} | {int(row['需求数量'])} | "
                         f"{row['总投入']:.1f} | {row['总价值分变动']:.2f} | "
                         f"{row['平均价值分变动']:.2f} | {row['投入产出比']:.2f} |")

    if not priority_stats.empty:
        report.append("\n### 3.2 按需求优先级分析\n")

        report.append("| 优先级 | 需求数量 | 总BG点数投入 | 总价值分变动 | 平均价值分变动 | 投入产出比 |")
        report.append("|--------|----------|--------------|--------------|----------------|------------|")

        sorted_priority = priority_stats.sort_values('投入产出比', ascending=False)
        for _, row in sorted_priority.iterrows():
            report.append(f"| {row['需求优先级']} | {int(row['需求数量'])} | "
                         f"{row['总投入']:.1f} | {row['总价值分变动']:.2f} | "
                         f"{row['平均价值分变动']:.2f} | {row['投入产出比']:.2f} |")

        # 高效需求类型
        report.append("\n### 3.3 效能最佳优先级\n")
        top_priority = sorted_priority.head(2)
        for i, (_, row) in enumerate(top_priority.iterrows(), 1):
            report.append(f"{i}. **{row['需求优先级']}**: 投入产出比 {row['投入产出比']:.2f}, "
                         f"平均价值分变动 {row['平均价值分变动']:.2f}")

        # 低效需求类型
        report.append("\n### 3.4 效能待提升优先级\n")
        bottom_priority = sorted_priority[sorted_priority['总投入'] > 0].tail(2)
        for i, (_, row) in enumerate(bottom_priority.iterrows(), 1):
            report.append(f"{i}. **{row['需求优先级']}**: 投入产出比 {row['投入产出比']:.2f}, "
                         f"平均价值分变动 {row['平均价值分变动']:.2f}")

    # 4. 问题诊断
    report.append("\n## 四、问题诊断与建议\n")

    if not problems.empty:
        report.append("### 4.1 问题车厢识别\n")

        for problem_type in problems['问题类型'].unique():
            report.append(f"\n**{problem_type}**:\n")
            type_problems = problems[problems['问题类型'] == problem_type]
            for _, row in type_problems.iterrows():
                report.append(f"- **{row['车厢']}**: {row['问题描述']}")
                report.append(f"  - 建议: {row['建议']}")
    else:
        report.append("未发现明显问题车厢。\n")

    # 5. 里程碑趋势分析
    report.append("\n## 五、里程碑趋势分析\n")

    if not df_req_value.empty and '里程碑' in df_req_value.columns:
        milestone_trend = df_req_value.groupby('里程碑').agg({
            '需求名称': 'count',
            '总投入': 'sum',
            '价值分变动': 'sum'
        }).reset_index()
        milestone_trend.columns = ['里程碑', '需求数量', '总BG点数投入', '总价值分变动']
        milestone_trend['投入产出比'] = np.where(
            milestone_trend['总BG点数投入'] > 0,
            milestone_trend['总价值分变动'] / milestone_trend['总BG点数投入'],
            0
        )

        report.append("| 里程碑 | 需求数量 | 总BG点数投入 | 总价值分变动 | 投入产出比 |")
        report.append("|--------|----------|--------------|--------------|------------|")

        for _, row in milestone_trend.iterrows():
            report.append(f"| {row['里程碑']} | {int(row['需求数量'])} | "
                         f"{row['总BG点数投入']:.1f} | {row['总价值分变动']:.2f} | "
                         f"{row['投入产出比']:.2f} |")

    # 6. 关键发现总结
    report.append("\n## 六、关键发现\n")

    # 最佳实践车厢
    best_carriage = combined.loc[combined['投入产出比'].idxmax()]
    report.append(f"\n1. **最高效车厢**: {best_carriage['车厢']}")
    report.append(f"   - 投入产出比: {best_carriage['投入产出比']:.2f}")
    report.append(f"   - 需求成功率: {best_carriage['需求成功率']:.1f}%")

    # 整体成功率
    if not success_rate.empty:
        overall_success_rate = success_rate['正向变动数'].sum() / success_rate['总需求数'].sum() * 100
        report.append(f"\n2. **整体需求成功率**: {overall_success_rate:.1f}%")

    # 总投入总产出
    total_input = combined['总投入'].sum()
    total_output = combined['总价值分变动'].sum()
    overall_roi = total_output / total_input if total_input > 0 else 0
    report.append(f"\n3. **整体投入产出比**: {overall_roi:.2f}")
    report.append(f"   - 总BG点数投入: {total_input:.1f} 点")
    report.append(f"   - 总价值分变动: {total_output:.2f} 分")

    # 4. 需求类型洞察
    if not priority_stats.empty:
        best_priority = priority_stats.loc[priority_stats['投入产出比'].idxmax()]
        worst_priority = priority_stats[priority_stats['总投入'] > 0].loc[
            priority_stats[priority_stats['总投入'] > 0]['投入产出比'].idxmin()
        ]
        report.append(f"\n4. **需求类型洞察**:")
        report.append(f"   - 效能最佳: {best_priority['需求优先级']} (投入产出比: {best_priority['投入产出比']:.2f})")
        report.append(f"   - 效能待提升: {worst_priority['需求优先级']} (投入产出比: {worst_priority['投入产出比']:.2f})")

    # 5. 建议行动
    report.append(f"\n5. **建议行动**:")
    report.append(f"   - 向高效车厢学习最佳实践")
    report.append(f"   - 优化低效车厢的需求选择机制")
    report.append(f"   - 增加创新需求比例（当前投入产出比最高）")
    report.append(f"   - 重新评估标准需求的投入价值")

    return '\n'.join(report)

def main():
    print("=" * 60)
    print("车厢效能评估分析")
    print("=" * 60)

    # 1. 加载里程碑数据
    print("\n【1】加载里程碑数据...")
    df_req = load_milestone_data()

    if df_req.empty:
        print("错误: 未能加载里程碑数据")
        return

    print(f"共加载 {len(df_req)} 条可进车厢的需求")

    # 2. 计算人日投入
    print("\n【2】计算人日投入...")
    df_req = calculate_resource_days(df_req)

    # 3. 加载价值分数据
    print("\n【3】加载价值分数据...")
    df_value = load_value_score_data()

    if df_value.empty:
        print("错误: 未能加载价值分数据")
        return

    # 4. 分析车厢效能
    print("\n【4】分析车厢效能...")
    carriage_efficiency, value_by_carriage = analyze_carriage_efficiency(df_req, df_value)
    print(f"分析了 {len(carriage_efficiency)} 个车厢")

    # 5. 分析需求成功率
    print("\n【5】分析需求成功率...")
    success_rate, df_req_value = analyze_requirement_success_rate(df_req, df_value)

    # 6. 分析需求类型
    print("\n【6】分析需求类型...")
    category_stats, priority_stats = analyze_requirement_types(df_req_value)

    # 7. 识别问题
    print("\n【7】识别问题车厢...")
    problems = identify_problems(carriage_efficiency, success_rate, df_req_value)

    # 8. 生成报告
    print("\n【8】生成效能评估报告...")
    report = generate_report(carriage_efficiency, success_rate, category_stats, priority_stats, problems, df_req_value)

    # 9. 保存报告
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, '07_车厢效能评估.md')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存至: {output_file}")

    # 10. 打印关键发现
    print("\n" + "=" * 60)
    print("关键发现摘要")
    print("=" * 60)

    print(f"\n1. 分析车厢数: {len(carriage_efficiency)}")
    print(f"2. 分析需求数: {len(df_req)}")
    print(f"3. 总BG点数投入: {df_req['总投入'].sum():.1f} 点")

    if not success_rate.empty:
        overall_success_rate = success_rate['正向变动数'].sum() / success_rate['总需求数'].sum() * 100
        print(f"4. 整体需求成功率: {overall_success_rate:.1f}%")

    print(f"5. 最高效车厢: {carriage_efficiency.loc[carriage_efficiency['投入产出比'].idxmax(), '车厢']}")

    if not problems.empty:
        print(f"6. 问题车厢数: {len(problems)}")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
