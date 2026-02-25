"""
供给模拟模块 - 模拟陪诊员状态管理
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np

from ..config.settings import SimulationConfig
from ..models.entities import Escort, EscortStatus


class SupplySimulator:
    """供给模拟器"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.escorts: Dict[str, Escort] = {}
        self.total_recruit_cost: float = 0.0

        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

        # 初始化陪诊员
        self._initialize_escorts()

    def _initialize_escorts(self):
        """初始化陪诊员池"""
        for _ in range(self.config.initial_escorts):
            escort = Escort(
                status=EscortStatus.TRAINING,
                join_date=datetime.now(),
                specialized_hospitals=random.sample(
                    self.config.covered_hospitals,
                    k=min(2, len(self.config.covered_hospitals))
                ),
                # 随机分配地理位置（北京市区范围）
                location_lat=random.uniform(39.8, 40.0),
                location_lon=random.uniform(116.2, 116.5),
                home_district=random.choice([
                    "朝阳", "海淀", "西城", "东城", "丰台",
                    "石景山", "昌平", "大兴", "通州", "房山"
                ]),
            )
            self.escorts[escort.id] = escort

    def daily_update(self, day: int):
        """每日更新供给状态"""
        # 1. 招募新人
        if day % 7 == 0 and day > 0:  # 每周招募
            self._recruit_new_escorts(day)

        # 2. 培训完成判定
        self._process_training_completion(day)

        # 3. 流失判定
        if day % 30 == 0 and day > 0:  # 每月判定流失
            self._process_churn()

        # 4. 重置每日接单计数
        self._reset_daily_capacity()

    def _recruit_new_escorts(self, day: int = 0):
        """招募新陪诊员（随时间递减的招募率）"""
        # 随时间递减的招募率
        week_number = day // 7
        decay = 1 - (self.config.recruit_decay_factor * week_number / 52)
        decay = max(decay, 0.4)  # 最低保留40%招募能力
        actual_recruit = int(self.config.weekly_recruit * decay)

        for _ in range(actual_recruit):
            escort = Escort(
                status=EscortStatus.TRAINING,
                join_date=datetime.now(),
                specialized_hospitals=random.sample(
                    self.config.covered_hospitals,
                    k=min(2, len(self.config.covered_hospitals))
                ),
                # 随机分配地理位置（北京市区范围）
                location_lat=random.uniform(39.8, 40.0),
                location_lon=random.uniform(116.2, 116.5),
                home_district=random.choice([
                    "朝阳", "海淀", "西城", "东城", "丰台",
                    "石景山", "昌平", "大兴", "通州", "房山"
                ]),
            )
            self.escorts[escort.id] = escort
            self.total_recruit_cost += self.config.recruit_cost

    def _process_training_completion(self, day: int):
        """处理培训完成"""
        for escort in self.escorts.values():
            if escort.status == EscortStatus.TRAINING:
                # 检查是否达到培训周期
                days_since_join = day
                if days_since_join >= self.config.training_days:
                    # 判定是否通过培训
                    if random.random() < self.config.training_pass_rate:
                        escort.status = EscortStatus.AVAILABLE
                        escort.training_complete_date = datetime.now() + timedelta(days=day)
                    else:
                        # 培训未通过，移除
                        escort.status = EscortStatus.CHURNED

    def get_income_tier(self, escort: Escort) -> str:
        """获取陪诊师收入分层"""
        if escort.total_orders == 0:
            return "low_income"
        # 估算月收入（假设每单平均200元x70%分成）
        avg_income_per_order = escort.total_income / max(1, escort.total_orders)
        monthly_income = avg_income_per_order * min(escort.total_orders, 30) * 0.7
        if monthly_income >= 7000:
            return "high_income"
        elif monthly_income >= 5000:
            return "medium_income"
        else:
            return "low_income"

    def _process_churn(self):
        """处理陪诊员流失（基于收入分层）"""
        # 收入分层流失率
        churn_rate_by_tier = {
            "high_income": 0.05,   # 高收入：5%/月
            "medium_income": 0.10, # 中收入：10%/月
            "low_income": 0.20,    # 低收入：20%/月
        }

        available_escorts = [
            e for e in self.escorts.values()
            if e.status in [EscortStatus.AVAILABLE, EscortStatus.REST]
        ]

        for escort in available_escorts:
            escort.update_churn_risk()
            tier = self.get_income_tier(escort)
            base_churn = churn_rate_by_tier[tier]
            churn_prob = base_churn * escort.churn_risk
            if random.random() < churn_prob:
                escort.status = EscortStatus.CHURNED

    def _reset_daily_capacity(self):
        """重置每日接单容量和当日收入"""
        for escort in self.escorts.values():
            if escort.status == EscortStatus.AVAILABLE:
                escort.current_daily_income = 0.0

    def get_available_escorts(self) -> List[Escort]:
        """获取可接单的陪诊员"""
        return [
            e for e in self.escorts.values()
            if e.status == EscortStatus.AVAILABLE
        ]

    def get_statistics(self) -> Dict:
        """获取供给侧统计数据"""
        total = len(self.escorts)
        by_status = {}
        for status in EscortStatus:
            count = sum(1 for e in self.escorts.values() if e.status == status)
            by_status[status.value] = count

        available = by_status.get(EscortStatus.AVAILABLE.value, 0)
        avg_income = np.mean([e.total_income for e in self.escorts.values()]) if total > 0 else 0
        avg_orders = np.mean([e.total_orders for e in self.escorts.values()]) if total > 0 else 0

        return {
            "total_escorts": total,
            "by_status": by_status,
            "available_escorts": available,
            "avg_income": avg_income,
            "avg_orders": avg_orders,
            "total_recruit_cost": self.total_recruit_cost,
        }
