"""
投诉处理模块 - 基于医疗健康营销案例数据
数据来源：integrated_data_config.py 中的 complaint_impact 配置

投诉率对转化率的影响：每↑1% → 转化率↓0.45%
目标投诉率：<1%（医疗行业标准）
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import numpy as np


class ComplaintType(Enum):
    """投诉类型"""
    MEDICAL_ADVICE_ERROR = "medical_advice_error"  # 医学建议错误（严重）
    HOSPITAL_CONFLICT = "hospital_conflict"          # 医院冲突（中等）
    SERVICE_QUALITY = "service_quality"              # 服务质量（最常见）
    OTHERS = "others"                                # 其他


class ComplaintStatus(Enum):
    """投诉状态"""
    PENDING = "待处理"
    IN_PROGRESS = "处理中"
    RESOLVED = "已解决"
    ESCALATED = "已升级"


@dataclass
class Complaint:
    """投诉记录"""
    id: str
    order_id: str
    user_id: str
    escort_id: Optional[str]
    complaint_type: ComplaintType
    status: ComplaintStatus = ComplaintStatus.PENDING
    created_day: int = 0
    resolved_day: Optional[int] = None
    resolution_hours: float = 0.0
    is_repurchased_after: bool = False  # 投诉后是否仍然复购
    severity: str = "medium"           # critical / medium / low
    compensation_amount: float = 0.0   # 赔偿金额


class ComplaintHandler:
    """
    投诉处理器

    基于医疗健康营销案例数据：
    - 投诉率每↑1% → 转化率↓0.45%
    - 目标投诉率：<1%
    - 投诉解决率目标：>95%（24小时内）
    - 复购救回率目标：>50%
    """

    # 投诉类型配置（来自 integrated_data_config.py）
    COMPLAINT_TYPE_CONFIG = {
        ComplaintType.MEDICAL_ADVICE_ERROR: {
            "ratio": 0.075,
            "severity": "critical",
            "resolution_hours": 168,   # 7天
            "compensation_ratio": 1.0, # 全额退款
        },
        ComplaintType.HOSPITAL_CONFLICT: {
            "ratio": 0.125,
            "severity": "medium",
            "resolution_hours": 24,
            "compensation_ratio": 0.5,
        },
        ComplaintType.SERVICE_QUALITY: {
            "ratio": 0.65,
            "severity": "medium",
            "resolution_hours": 48,
            "compensation_ratio": 0.3,
        },
        ComplaintType.OTHERS: {
            "ratio": 0.15,
            "severity": "low",
            "resolution_hours": 72,
            "compensation_ratio": 0.1,
        },
    }

    # 投诉率对转化率的影响系数
    COMPLAINT_CONVERSION_IMPACT = -0.0045  # 每↑1% → 转化率↓0.45%

    def __init__(self):
        self.complaints: List[Complaint] = []
        self.current_day: int = 0

        self.total_complaints: int = 0
        self.resolved_complaints: int = 0
        self.repurchased_after_complaint: int = 0

        self.current_complaint_rate: float = 0.0
        self.conversion_rate_modifier: float = 1.0
        self.complaints_by_type: Dict[str, int] = {t.value: 0 for t in ComplaintType}

        # 滑动窗口：记录近30天每日订单数（修复 Bug #3）
        self._daily_orders_window: List[int] = []

    def generate_complaint(self, order_id: str, user_id: str,
                           escort_id: Optional[str], order_price: float,
                           day: int) -> Optional[Complaint]:
        """
        基于服务失败生成投诉

        Args:
            order_id: 订单ID
            user_id: 用户ID
            escort_id: 陪诊员ID
            order_price: 订单金额
            day: 当前模拟天数

        Returns:
            Complaint 或 None（不是所有失败都会投诉）
        """
        # 服务失败后约30%概率产生投诉（医疗行业特点：用户维权意识较低）
        if random.random() > 0.30:
            return None

        # 按比例随机选择投诉类型
        complaint_type = self._sample_complaint_type()
        config = self.COMPLAINT_TYPE_CONFIG[complaint_type]

        # 计算赔偿金额
        compensation = order_price * config["compensation_ratio"]

        complaint = Complaint(
            id=f"complaint_{day}_{len(self.complaints)}",
            order_id=order_id,
            user_id=user_id,
            escort_id=escort_id,
            complaint_type=complaint_type,
            status=ComplaintStatus.PENDING,
            created_day=day,
            severity=config["severity"],
            compensation_amount=compensation,
        )

        self.complaints.append(complaint)
        self.total_complaints += 1
        self.complaints_by_type[complaint_type.value] += 1

        return complaint

    def process_daily_complaints(self, current_day: int, total_orders: int):
        """
        处理当日投诉（模拟投诉处理流程）

        Args:
            current_day: 当前模拟天数
            total_orders: 当日总订单数（用于计算投诉率）
        """
        self.current_day = current_day

        # 处理待处理的投诉
        for complaint in self.complaints:
            if complaint.status == ComplaintStatus.PENDING:
                complaint.status = ComplaintStatus.IN_PROGRESS

            elif complaint.status == ComplaintStatus.IN_PROGRESS:
                config = self.COMPLAINT_TYPE_CONFIG[complaint.complaint_type]
                days_since_created = current_day - complaint.created_day
                required_days = config["resolution_hours"] / 24

                # 判断是否已解决
                if days_since_created >= required_days:
                    # 95%概率解决（目标解决率）
                    if random.random() < 0.95:
                        complaint.status = ComplaintStatus.RESOLVED
                        complaint.resolved_day = current_day
                        complaint.resolution_hours = days_since_created * 24
                        self.resolved_complaints += 1

                        # 50%概率投诉后仍然复购（复购救回率）
                        if random.random() < 0.50:
                            complaint.is_repurchased_after = True
                            self.repurchased_after_complaint += 1
                    else:
                        complaint.status = ComplaintStatus.ESCALATED

        # 更新投诉率和转化率修正系数
        self._update_complaint_rate(total_orders)

    def _sample_complaint_type(self) -> ComplaintType:
        """按比例随机选择投诉类型（使用 random.choices 避免浮点精度问题）"""
        types = list(self.COMPLAINT_TYPE_CONFIG.keys())
        weights = [self.COMPLAINT_TYPE_CONFIG[t]["ratio"] for t in types]
        return random.choices(types, weights=weights, k=1)[0]

    def _update_complaint_rate(self, today_orders: int):
        """更新投诉率和转化率修正系数（使用滑动窗口，修复 Bug #3）"""
        # 维护近30天订单数滑动窗口
        self._daily_orders_window.append(today_orders)
        if len(self._daily_orders_window) > 30:
            self._daily_orders_window.pop(0)

        recent_orders = sum(self._daily_orders_window)
        if recent_orders <= 0:
            return

        # 近30天投诉数
        recent_complaints = sum(
            1 for c in self.complaints
            if self.current_day - c.created_day <= 30
        )

        self.current_complaint_rate = recent_complaints / recent_orders

        # 投诉率每↑1% → 转化率↓0.45%
        complaint_rate_pct = self.current_complaint_rate * 100
        impact = self.COMPLAINT_CONVERSION_IMPACT * complaint_rate_pct
        self.conversion_rate_modifier = max(0.5, 1.0 + impact)

    def get_conversion_rate_modifier(self) -> float:
        """获取当前转化率修正系数（供需求模块使用）"""
        return self.conversion_rate_modifier

    def get_statistics(self) -> Dict:
        """获取投诉统计数据"""
        resolution_rate = (
            self.resolved_complaints / self.total_complaints
            if self.total_complaints > 0 else 0
        )
        repurchase_recovery_rate = (
            self.repurchased_after_complaint / self.resolved_complaints
            if self.resolved_complaints > 0 else 0
        )

        return {
            "total_complaints": self.total_complaints,
            "resolved_complaints": self.resolved_complaints,
            "pending_complaints": sum(
                1 for c in self.complaints
                if c.status in (ComplaintStatus.PENDING, ComplaintStatus.IN_PROGRESS)
            ),
            "resolution_rate": resolution_rate,
            "repurchase_recovery_rate": repurchase_recovery_rate,
            "current_complaint_rate": self.current_complaint_rate,
            "conversion_rate_modifier": self.conversion_rate_modifier,
            "complaints_by_type": self.complaints_by_type,
            # 健康指标
            "is_complaint_rate_healthy": self.current_complaint_rate < 0.01,
            "is_resolution_rate_healthy": resolution_rate > 0.95,
        }
