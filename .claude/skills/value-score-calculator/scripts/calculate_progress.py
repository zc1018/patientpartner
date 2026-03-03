#!/usr/bin/env python3
"""
价值分进度计算器
计算 L1/L2/L3 进度和总进度
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List


# 系统名称映射（通晒表格 -> 统计表）
SYSTEM_MAPPING = {
    'A慧刷题项目': '慧刷题',
    'A哪吒系统 (在线版）': '哪吒系统（在线版）',
    'A择校': '择校',
    'B慧学系统': '慧学系统',
    'C轻学': '轻学',
    'C售后平台': '售后平台',
    '投放平台': '投放系统'
}


def calculate_progress(current: float, month_value: float, target: float) -> Optional[float]:
    """
    计算进度

    公式: (当月值 - 现状值) / (目标值 - 现状值)

    Args:
        current: 现状值
        month_value: 当月实际值
        target: 目标值

    Returns:
        进度值（小数形式，如 0.5 表示 50%），计算失败返回 None
    """
    if pd.isna(month_value) or pd.isna(current) or pd.isna(target):
        return None

    if target == current:
        return 1.0 if month_value >= target else 0.0

    return (month_value - current) / (target - current)


def calculate_total_progress(l1_progress: Optional[float],
                            l2_progress: Optional[float],
                            l3_progress: Optional[float]) -> Optional[float]:
    """
    计算总进度（三项进度的平均值）

    Args:
        l1_progress: L1进度
        l2_progress: L2进度
        l3_progress: L3进度

    Returns:
        总进度（有效进度的平均值），无有效值返回 None
    """
    progress_list = [p for p in [l1_progress, l2_progress, l3_progress] if p is not None and pd.notna(p)]

    if not progress_list:
        return None

    return np.mean(progress_list)


def get_system_mapping(system_name: str) -> Optional[str]:
    """
    获取系统名称映射

    Args:
        system_name: 通晒表格中的系统名

    Returns:
        统计表中的系统名，无映射返回 None
    """
    return SYSTEM_MAPPING.get(system_name)


def format_progress_as_percentage(progress: Optional[float]) -> str:
    """
    将进度格式化为百分比字符串

    Args:
        progress: 进度值（小数形式）

    Returns:
        百分比字符串，如 "50.00%"
    """
    if progress is None or pd.isna(progress):
        return "N/A"
    return f"{progress * 100:.2f}%"


def interpret_progress(progress: Optional[float]) -> str:
    """
    解读进度含义

    Args:
        progress: 进度值

    Returns:
        进度状态描述
    """
    if progress is None or pd.isna(progress):
        return "⚪ 无数据"
    elif progress >= 1.0:
        return "🟢 达成目标"
    elif progress >= 0.5:
        return "🟡 进展良好"
    elif progress >= 0:
        return "🟠 进展缓慢"
    else:
        return "🔴 退步"


if __name__ == "__main__":
    # 测试示例
    print("=== 进度计算测试 ===")

    # 示例1: 正常进度
    p1 = calculate_progress(10, 15, 20)
    print(f"示例1 - 现状10→目标20，当月15: 进度 = {format_progress_as_percentage(p1)} ({interpret_progress(p1)})")

    # 示例2: 退步
    p2 = calculate_progress(10, 5, 20)
    print(f"示例2 - 现状10→目标20，当月5: 进度 = {format_progress_as_percentage(p2)} ({interpret_progress(p2)})")

    # 示例3: 超额完成
    p3 = calculate_progress(10, 25, 20)
    print(f"示例3 - 现状10→目标20，当月25: 进度 = {format_progress_as_percentage(p3)} ({interpret_progress(p3)})")

    # 示例4: 总进度
    total = calculate_total_progress(p1, p2, p3)
    print(f"总进度 = {format_progress_as_percentage(total)}")
