"""
用户生命周期追踪模块 - 基于真实留存率数据
数据来源：integrated_data_config.py 中的 user_churn_rate 配置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd
import numpy as np


class UserSegment(Enum):
    """用户分层"""
    FIRST_ORDER = "首单用户"      # 1单
    DEVELOPING = "发展中用户"      # 2-3单
    REGULAR = "老客"              # 4单+


@dataclass
class UserLifecycleRecord:
    """用户生命周期记录"""
    user_id: str
    first_order_date: int  # 模拟天数（第几天首次下单）
    last_active_date: int  # 最后活跃日期（模拟天数）
    total_orders: int = 0
    segment: UserSegment = UserSegment.FIRST_ORDER

    # 留存状态
    is_active: bool = True
    is_churned: bool = False
    churn_date: Optional[int] = None

    # 指定陪诊师信息
    designated_escort_id: Optional[str] = None
    has_designated_escort: bool = False

    # 评分历史
    ratings: List[float] = field(default_factory=list)
    avg_rating: float = 0.0

    def update_segment(self):
        """根据订单数更新用户分层"""
        if self.total_orders >= 4:
            self.segment = UserSegment.REGULAR
        elif self.total_orders >= 2:
            self.segment = UserSegment.DEVELOPING
        else:
            self.segment = UserSegment.FIRST_ORDER

    def record_order(self, order_day: int, rating: Optional[float] = None):
        """记录订单"""
        self.total_orders += 1
        self.last_active_date = order_day
        self.update_segment()

        if rating is not None:
            self.ratings.append(rating)
            self.avg_rating = sum(self.ratings) / len(self.ratings)

    def mark_churned(self, churn_day: int):
        """标记用户流失"""
        self.is_active = False
        self.is_churned = True
        self.churn_date = churn_day


@dataclass
class CohortRetentionMetrics:
    """Cohort 留存指标"""
    cohort_date: int  # cohort 起始日期（模拟天数）
    cohort_size: int  # 初始用户数

    # 各时间点留存用户数
    retention_by_day: Dict[int, int] = field(default_factory=dict)

    # 各时间点留存率
    retention_rates: Dict[int, float] = field(default_factory=dict)

    def calculate_retention_rate(self, day: int) -> float:
        """计算指定日期的留存率"""
        if self.cohort_size == 0:
            return 0.0
        retained = self.retention_by_day.get(day, 0)
        return retained / self.cohort_size


class UserLifecycleTracker:
    """
    用户生命周期追踪器

    基于真实留存率数据追踪用户：
    - 首单用户：30天留存率45%，90天留存率36%
    - 2-3单用户：90天留存率45%
    - 4单+老客：90天留存率75%
    """

    def __init__(self):
        # 用户生命周期记录 {user_id: UserLifecycleRecord}
        self.user_records: Dict[str, UserLifecycleRecord] = {}

        # Cohort 分组 {cohort_day: {user_id: UserLifecycleRecord}}
        self.cohorts: Dict[int, Dict[str, UserLifecycleRecord]] = {}

        # 历史留存率数据用于分析
        self.retention_history: List[Dict] = []

        # 当前模拟天数
        self.current_day: int = 0

        # 统计指标
        self.metrics = {
            'total_registered': 0,
            'total_active': 0,
            'total_churned': 0,
            'by_segment': {
                'FIRST_ORDER': {'active': 0, 'churned': 0},
                'DEVELOPING': {'active': 0, 'churned': 0},
                'REGULAR': {'active': 0, 'churned': 0},
            }
        }

        # 留存率配置
        self.churn_config = {
            'first_order_users': {
                'monthly_churn': 0.55,
                '30_day_retention': 0.45,
                '90_day_retention': 0.36,
                '180_day_retention': 0.25,
            },
            '2_3_order_users': {
                'monthly_churn': 0.25,
                '90_day_retention': 0.45,
            },
            '4_plus_order_users': {
                'monthly_churn': 0.10,
                '90_day_retention': 0.75,
            }
        }

    def register_user(self, user_id: str, order_day: int,
                      designated_escort_id: Optional[str] = None) -> UserLifecycleRecord:
        """
        注册新用户（首次下单）

        Args:
            user_id: 用户ID
            order_day: 下单日期（模拟天数）
            designated_escort_id: 指定陪诊师ID（如有）

        Returns:
            UserLifecycleRecord: 用户生命周期记录
        """
        record = UserLifecycleRecord(
            user_id=user_id,
            first_order_date=order_day,
            last_active_date=order_day,
            total_orders=1,
            segment=UserSegment.FIRST_ORDER,
            designated_escort_id=designated_escort_id,
            has_designated_escort=designated_escort_id is not None
        )

        self.user_records[user_id] = record

        # 添加到 cohort
        if order_day not in self.cohorts:
            self.cohorts[order_day] = {}
        self.cohorts[order_day][user_id] = record

        # 更新统计
        self.metrics['total_registered'] += 1
        self.metrics['total_active'] += 1
        self.metrics['by_segment']['FIRST_ORDER']['active'] += 1

        return record

    def update_user_activity(self, user_id: str, order_day: int,
                            rating: Optional[float] = None,
                            designated_escort_id: Optional[str] = None):
        """
        更新用户活跃状态（复购）

        Args:
            user_id: 用户ID
            order_day: 下单日期（模拟天数）
            rating: 用户评分（可选）
            designated_escort_id: 指定陪诊师ID（可选）
        """
        if user_id not in self.user_records:
            # 新用户，自动注册
            self.register_user(user_id, order_day, designated_escort_id)
            return

        record = self.user_records[user_id]

        # 更新指定陪诊师
        if designated_escort_id and not record.has_designated_escort:
            record.designated_escort_id = designated_escort_id
            record.has_designated_escort = True

        # 记录订单
        old_segment = record.segment
        record.record_order(order_day, rating)

        # 更新分层统计
        if old_segment != record.segment:
            self.metrics['by_segment'][old_segment.name]['active'] -= 1
            self.metrics['by_segment'][record.segment.name]['active'] += 1

    def mark_user_churned(self, user_id: str, churn_day: int):
        """
        标记用户流失

        Args:
            user_id: 用户ID
            churn_day: 流失日期（模拟天数）
        """
        if user_id not in self.user_records:
            return

        record = self.user_records[user_id]
        if record.is_churned:
            return

        record.mark_churned(churn_day)

        # 更新统计
        self.metrics['total_active'] -= 1
        self.metrics['total_churned'] += 1
        self.metrics['by_segment'][record.segment.name]['active'] -= 1
        self.metrics['by_segment'][record.segment.name]['churned'] += 1

    def simulate_daily_churn(self, current_day: int) -> List[str]:
        """
        基于真实留存率模拟每日用户流失

        Args:
            current_day: 当前模拟天数

        Returns:
            List[str]: 当日流失的用户ID列表
        """
        self.current_day = current_day
        churned_users = []

        for user_id, record in self.user_records.items():
            if not record.is_active or record.is_churned:
                continue

            days_since_first = current_day - record.first_order_date

            # 根据用户分层获取留存率配置
            if record.segment == UserSegment.FIRST_ORDER:
                config = self.churn_config['first_order_users']
                retention_30d = config['30_day_retention']
                retention_90d = config['90_day_retention']

                # 计算流失概率（基于留存曲线）
                if days_since_first <= 30:
                    # 前30天：从100%降到45%
                    daily_churn_prob = (1 - retention_30d) / 30 * 1.5  # 前期流失更快
                else:
                    # 30-90天：从45%降到36%
                    daily_churn_prob = (retention_30d - retention_90d) / 60

            elif record.segment == UserSegment.DEVELOPING:
                config = self.churn_config['2_3_order_users']
                retention_90d = config['90_day_retention']

                # 2-3单用户90天留存率45%
                daily_churn_prob = (1 - retention_90d) / 90 * 0.8  # 流失较慢

            else:  # REGULAR
                config = self.churn_config['4_plus_order_users']
                retention_90d = config['90_day_retention']

                # 4单+老客90天留存率75%
                daily_churn_prob = (1 - retention_90d) / 90 * 0.5  # 流失很慢

            # 评分影响：评分低的用户更容易流失
            if record.avg_rating > 0:
                if record.avg_rating >= 4.8:
                    daily_churn_prob *= 0.7  # 高分用户流失率降低30%
                elif record.avg_rating >= 4.5:
                    daily_churn_prob *= 1.0  # 正常
                elif record.avg_rating >= 4.0:
                    daily_churn_prob *= 1.5  # 低分用户流失率增加50%
                else:
                    daily_churn_prob *= 2.5  # 很差评分流失率增加150%

            # 指定陪诊师保护效应
            if record.has_designated_escort:
                daily_churn_prob *= 0.5  # 有指定陪诊师的用户流失率减半

            # 随机判断是否流失
            if np.random.random() < daily_churn_prob:
                self.mark_user_churned(user_id, current_day)
                churned_users.append(user_id)

        return churned_users

    def get_retention_curve(self, segment: Optional[UserSegment] = None,
                           max_days: int = 180) -> Dict[int, float]:
        """
        获取留存曲线数据

        Args:
            segment: 用户分层（None表示全部用户）
            max_days: 最大天数

        Returns:
            Dict[int, float]: {天数: 留存率}
        """
        curve = {}

        for day in range(0, max_days + 1, 7):  # 每周一个点
            if day == 0:
                curve[day] = 1.0
                continue

            total_users = 0
            retained_users = 0

            for user_id, record in self.user_records.items():
                # 筛选特定分层
                if segment and record.segment != segment:
                    continue

                # 只统计已经存在day天的用户
                if record.first_order_date + day > self.current_day:
                    continue

                total_users += 1

                # 判断是否在day天后仍然留存
                if not record.is_churned:
                    retained_users += 1
                elif record.churn_date and record.churn_date > record.first_order_date + day:
                    retained_users += 1

            curve[day] = retained_users / total_users if total_users > 0 else 0

        return curve

    def get_segment_retention_rates(self, day: int = 30) -> Dict[str, float]:
        """
        获取各分层的留存率

        Args:
            day: 观察天数（默认30天）

        Returns:
            Dict[str, float]: {分层名称: 留存率}
        """
        rates = {}

        for segment in UserSegment:
            total = 0
            retained = 0

            for record in self.user_records.values():
                if record.segment != segment:
                    continue

                days_since_first = self.current_day - record.first_order_date
                if days_since_first < day:
                    continue  # 用户存在时间不足

                total += 1

                if not record.is_churned:
                    retained += 1
                elif record.churn_date and record.churn_date > record.first_order_date + day:
                    retained += 1

            rates[segment.value] = retained / total if total > 0 else 0

        return rates

    def get_lifecycle_report(self) -> Dict:
        """
        生成生命周期分析报告

        Returns:
            Dict: 包含各项生命周期指标的字典
        """
        # 计算真实的30天和90天留存率
        retention_30d = self.get_segment_retention_rates(day=30)
        retention_90d = self.get_segment_retention_rates(day=90)

        # 计算平均LTV（基于留存率）
        avg_orders_per_user = np.mean([
            r.total_orders for r in self.user_records.values()
        ]) if self.user_records else 0

        report = {
            'summary': {
                'total_registered': self.metrics['total_registered'],
                'total_active': self.metrics['total_active'],
                'total_churned': self.metrics['total_churned'],
                'churn_rate': self.metrics['total_churned'] / self.metrics['total_registered']
                              if self.metrics['total_registered'] > 0 else 0,
                'avg_orders_per_user': avg_orders_per_user,
            },
            'by_segment': self.metrics['by_segment'],
            'retention_rates': {
                '30_day': retention_30d,
                '90_day': retention_90d,
            },
            'config_comparison': {
                'first_order_30d': {
                    'actual': retention_30d.get('首单用户', 0),
                    'target': self.churn_config['first_order_users']['30_day_retention'],
                    'gap': retention_30d.get('首单用户', 0) - self.churn_config['first_order_users']['30_day_retention']
                },
                'first_order_90d': {
                    'actual': retention_90d.get('首单用户', 0),
                    'target': self.churn_config['first_order_users']['90_day_retention'],
                    'gap': retention_90d.get('首单用户', 0) - self.churn_config['first_order_users']['90_day_retention']
                }
            }
        }

        return report

    def export_cohort_data(self) -> pd.DataFrame:
        """
        导出 cohort 数据用于可视化

        Returns:
            pd.DataFrame: cohort 分析数据
        """
        data = []

        for cohort_day, users in self.cohorts.items():
            for user_id, record in users.items():
                data.append({
                    'cohort_day': cohort_day,
                    'user_id': user_id,
                    'first_order_date': record.first_order_date,
                    'last_active_date': record.last_active_date,
                    'total_orders': record.total_orders,
                    'segment': record.segment.value,
                    'is_active': record.is_active,
                    'is_churned': record.is_churned,
                    'churn_date': record.churn_date,
                    'has_designated_escort': record.has_designated_escort,
                    'avg_rating': record.avg_rating,
                    'lifetime_days': (record.churn_date or self.current_day) - record.first_order_date
                                     if record.churn_date else self.current_day - record.first_order_date
                })

        return pd.DataFrame(data)
