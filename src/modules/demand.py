# ============================================================================
# 基础版需求生成器 - 当前主版本，被 simulation/simulation.py (v2.0) 使用
# 增强版见 demand_enhanced.py（基于北京真实数据，尚未集成到主流程）
# ============================================================================
"""
需求生成模块 - 模拟用户订单生成
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

from ..config.settings import SimulationConfig
from ..models.entities import User, Order
from .geo_matcher import GeoMatcher


class DemandGenerator:
    """需求生成器"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.repurchase_pool: Dict[str, User] = {}  # 复购用户池
        self.geo_matcher = GeoMatcher()             # 地理位置匹配器
        self.conversion_rate_modifier: float = 1.0  # 投诉率影响的转化率修正系数
        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

    def set_conversion_rate_modifier(self, modifier: float):
        """设置转化率修正系数（由 complaint_handler 提供）"""
        self.conversion_rate_modifier = max(0.5, min(1.0, modifier))

    def generate_daily_orders(self, day: int) -> List[Order]:
        """生成当日订单需求"""
        base_orders = self._calculate_base_demand()
        actual_orders = self._apply_volatility(base_orders)
        new_orders = self._generate_new_user_orders(actual_orders, day)
        repurchase_orders = self._generate_repurchase_orders(day)
        return new_orders + repurchase_orders

    def _calculate_base_demand(self) -> float:
        """计算基础需求量（漏斗转化，含投诉率修正）"""
        funnel = (
            self.config.dau_base
            * self.config.exposure_rate
            * self.config.click_rate
            * self.config.consult_rate
            * self.config.order_rate
            * self.conversion_rate_modifier  # 投诉率影响
        )
        return funnel

    def _apply_volatility(self, base_demand: float) -> int:
        """应用需求波动"""
        volatility = np.random.normal(0, self.config.demand_volatility)
        actual = base_demand * (1 + volatility)
        return max(0, int(actual))

    def _generate_new_user_orders(self, count: int, day: int) -> List[Order]:
        """生成新用户订单"""
        orders = []
        for _ in range(count):
            user = self._create_user(is_repurchase=False)
            order = self._create_order(user, day)
            orders.append(order)
        return orders

    def _generate_repurchase_orders(self, day: int) -> List[Order]:
        """生成复购订单 - 基于用户分层的差异化复购率"""
        orders = []
        for user_id, user in list(self.repurchase_pool.items()):
            if day % self.config.repurchase_cycle_days == 0:
                repurchase_prob = self._get_repurchase_prob(user)
                if random.random() < repurchase_prob:
                    user.is_repurchase = True
                    user.total_orders += 1
                    order = self._create_order(user, day)
                    orders.append(order)
        return orders

    def _get_repurchase_prob(self, user: User) -> float:
        """
        根据用户类型获取复购率

        分层逻辑（基于 integrated_data_config.py）：
        - 指定陪诊师用户：82%（关键杠杆）
        - 子女代购用户（首单）：13.5%，老客：45%
        - 老年自主用户（首单）：13.5%，老客：22.5%
        """
        if user.has_designated_escort():
            return 0.82

        if user.total_orders <= 1:
            return self.config.repurchase_prob  # 0.135

        if user.is_children_purchase:
            return 0.45
        else:
            return 0.225

    def _create_user(self, is_repurchase: bool = False) -> User:
        """
        创建用户对象 - 实现子女代购分层 + 地理位置分配

        子女代购（80%）vs 老年自主（20%）：
        - 子女代购：复购率45%，价格敏感度中等
        - 老年自主：复购率22.5%，价格敏感度高
        """
        is_children_purchase = random.random() < 0.80
        lat, lon, district = self.geo_matcher.assign_user_location(None)

        user = User(
            target_hospital=random.choice(self.config.covered_hospitals),
            disease_type=random.choice(self.config.disease_types),
            service_period=random.choice(["上午", "下午", "全天"]),
            price_sensitivity=(
                random.uniform(0.3, 0.6) if is_children_purchase
                else random.uniform(0.6, 0.9)
            ),
            is_repurchase=is_repurchase,
            total_orders=1 if not is_repurchase else 0,
            is_children_purchase=is_children_purchase,
            location_lat=lat,
            location_lon=lon,
            location_district=district,
        )
        return user

    def _create_order(self, user: User, day: int) -> Order:
        """创建订单对象"""
        price = max(50, np.random.normal(
            self.config.price_mean,
            self.config.price_std
        ))
        return Order(
            user=user,
            price=round(price, 2),
            created_at=datetime.now() + timedelta(days=day),
        )

    def add_to_repurchase_pool(self, user: User):
        """将用户加入复购池"""
        self.repurchase_pool[user.id] = user
