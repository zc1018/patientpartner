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


# 年龄分层行为差异模型（从 user_behavior_agent 导入）
AGE_BEHAVIOR = {
    "60-70": {"children_purchase_rate": 0.4, "price_sensitivity": 0.6, "is_app_capable": True,  "repurchase_cycle_days": 180},
    "70-80": {"children_purchase_rate": 0.7, "price_sensitivity": 0.7, "is_app_capable": True,  "repurchase_cycle_days": 90},
    "80+":   {"children_purchase_rate": 0.9, "price_sensitivity": 0.5, "is_app_capable": False, "repurchase_cycle_days": 45},
}


def _get_age_group(age: int) -> str:
    """根据年龄返回分层key"""
    if age < 70:
        return "60-70"
    elif age < 80:
        return "70-80"
    else:
        return "80+"


def _generate_user_age() -> int:
    """生成用户年龄（60-90岁，正态分布偏向前高龄）"""
    # 使用截断正态分布：均值75，标准差8，范围60-90
    age = int(np.random.normal(75, 8))
    return max(60, min(90, age))


class DemandGenerator:
    """需求生成器"""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.repurchase_pool: Dict[str, User] = {}  # 复购用户池
        self.geo_matcher = GeoMatcher()             # 地理位置匹配器
        self.conversion_rate_modifier: float = 1.0  # 投诉率影响的转化率修正系数
        self._current_avg_price: float = getattr(config, 'price_mean', 250)  # 当前平均客单价
        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

    def _update_user_lifecycle_states(self) -> None:
        """
        每天更新用户生命周期状态（基于分层流失率）

        分层流失率（来自 integrated_data_config.py）:
        - 首单用户：月流失率 55%（日均约 1.83%）
        - 2-3单用户：月流失率 25%（日均约 0.83%）
        - 4单+老客：月流失率 10%（日均约 0.33%）
        """
        for user in self.repurchase_pool.values():
            user.days_since_last_order += 1

            # 根据订单历史确定流失率
            if user.total_orders == 1:
                daily_churn_rate = 0.55 / 30  # 首单用户
            elif user.total_orders <= 3:
                daily_churn_rate = 0.25 / 30  # 2-3单用户
            else:
                daily_churn_rate = 0.10 / 30  # 老客

            # 使用随机数判断是否流失
            if random.random() < daily_churn_rate:
                user.lifecycle_state = "churned"
            elif user.days_since_last_order > 30:
                user.lifecycle_state = "at_risk"

    def _remove_churned_users(self) -> None:
        """移除已流失用户（lifecycle_state == 'churned'）"""
        churned = [uid for uid, u in self.repurchase_pool.items()
                   if u.lifecycle_state == "churned"]
        for uid in churned:
            del self.repurchase_pool[uid]

    def set_conversion_rate_modifier(self, modifier: float):
        """设置转化率修正系数（由 complaint_handler 提供）"""
        self.conversion_rate_modifier = max(0.5, min(1.0, modifier))

    def set_current_avg_price(self, avg_price: float):
        """设置当前平均客单价（由外部模块提供）"""
        self._current_avg_price = avg_price

    def generate_daily_orders(self, day: int) -> List[Order]:
        """生成当日订单需求"""
        # 更新用户生命周期状态（每日）
        self._update_user_lifecycle_states()
        self._remove_churned_users()

        base_orders = self._calculate_base_demand()

        # 价格弹性调整：价格高于基准时需求下降
        base_price = getattr(self.config, 'base_price', 250)
        price_change_pct = (self._current_avg_price - base_price) / base_price
        price_elasticity = -1.2
        demand_adjustment = 1 + price_elasticity * price_change_pct
        base_orders = base_orders * max(0.3, demand_adjustment)

        # 周内差异 vs 月末效应（互斥，周末优先）
        day_of_week = day % 7
        day_of_month = (day % 30) + 1
        if day_of_week in [5, 6]:
            time_factor = 0.8   # 周末需求下降20%
        elif day_of_month >= 25:
            time_factor = 1.15  # 月末就医高峰+15%
        else:
            time_factor = 1.0

        # 应用系数到订单数量
        base_orders = base_orders * time_factor

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
        """生成复购订单 - 基于用户年龄分层的差异化复购周期"""
        orders = []
        for _, user in list(self.repurchase_pool.items()):
            # 根据年龄获取复购周期
            age_group = _get_age_group(user.age)
            cycle = AGE_BEHAVIOR[age_group].get("repurchase_cycle_days", 30)
            if user.days_since_last_order < cycle:
                continue
            repurchase_prob = self._get_repurchase_prob(user)
            if random.random() < repurchase_prob:
                user.is_repurchase = True
                user.total_orders += 1
                user.days_since_last_order = 0
                user.lifecycle_state = "active"
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
        创建用户对象 - 实现年龄分层 + 子女代购分层 + 地理位置分配

        年龄分层（AGE_BEHAVIOR）：
        - 60-70岁：子女代购率40%，价格敏感度0.6，能独立使用App
        - 70-80岁：子女代购率70%，价格敏感度0.7，能独立使用App
        - 80+岁：子女代购率90%，价格敏感度0.5，不能独立使用App
        """
        # 1. 生成用户年龄
        age = _generate_user_age()
        age_group = _get_age_group(age)
        behavior = AGE_BEHAVIOR[age_group]

        # 2. 根据年龄分层确定子女代购率
        is_children_purchase = random.random() < behavior["children_purchase_rate"]
        lat, lon, district = self.geo_matcher.assign_user_location(None)

        user = User(
            target_hospital=random.choice(self.config.covered_hospitals),
            disease_type=random.choice(self.config.disease_types),
            service_period=random.choice(["上午", "下午", "全天"]),
            price_sensitivity=behavior["price_sensitivity"],
            is_repurchase=is_repurchase,
            total_orders=1 if not is_repurchase else 0,
            is_children_purchase=is_children_purchase,
            location_lat=lat,
            location_lon=lon,
            location_district=district,
            age=age,
            is_app_capable=behavior["is_app_capable"],
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
        """将用户加入复购池并重置生命周期状态"""
        user.days_since_last_order = 0
        user.lifecycle_state = "active"
        self.repurchase_pool[user.id] = user
