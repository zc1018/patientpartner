# ============================================================================
# 增强版需求生成器 - 尚未集成到主流程
# 基础版见 demand.py（当前主版本，被 simulation/simulation.py 使用）
# 版本关系：demand.py 是 v1.0（漏斗模型），本文件是 v2.0（多渠道+真实数据）
# 集成方式：未来可在 simulation/ 下新建 EnhancedSimulation 子类使用本模块
# ============================================================================
"""
增强版需求生成模块 - 基于北京真实数据
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

from ..config.settings import SimulationConfig
from ..config.beijing_real_data import BeijingRealDataConfig
from ..models.entities import User, Order, OrderStatus


# 年龄分层行为差异模型
AGE_BEHAVIOR = {
    "60-70": {"children_purchase_rate": 0.4, "price_sensitivity": 0.6, "is_app_capable": True},
    "70-80": {"children_purchase_rate": 0.7, "price_sensitivity": 0.7, "is_app_capable": True},
    "80+":   {"children_purchase_rate": 0.9, "price_sensitivity": 0.5, "is_app_capable": False},
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
    age = int(np.random.normal(75, 8))
    return max(60, min(90, age))


class EnhancedDemandGenerator:
    """增强版需求生成器 - 考虑真实数据"""

    def __init__(self, config: SimulationConfig, beijing_data: BeijingRealDataConfig):
        self.config = config
        self.beijing_data = beijing_data
        self.repurchase_pool: Dict[str, User] = {}

        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

        # 预计算医院权重（基于门诊量）
        self.hospital_weights = self._calculate_hospital_weights()

        # 预计算区域权重（基于人口）
        self.district_weights = self._calculate_district_weights()

        # 加载时段需求系数
        self.hourly_demand_factors: Dict[str, float] = getattr(
            beijing_data, 'hourly_demand_factors', {}
        )
        if not self.hourly_demand_factors and hasattr(beijing_data, '__dict__'):
            self.hourly_demand_factors = beijing_data.__dict__.get('hourly_demand_factors', {})

    def _calculate_hospital_weights(self) -> Dict[str, float]:
        """计算医院权重（基于门诊量和老年人比例）"""
        weights = {}
        total = sum(
            h["daily_visits"] * h["elderly_ratio"]
            for h in self.beijing_data.hospitals
        )
        for hospital in self.beijing_data.hospitals:
            weight = (hospital["daily_visits"] * hospital["elderly_ratio"]) / total
            weights[hospital["name"]] = weight
        return weights

    def _calculate_district_weights(self) -> Dict[str, float]:
        """计算区域权重（基于人口）"""
        weights = {}
        total = sum(d["population"] for d in self.beijing_data.district_payment_ability.values())
        for district, data in self.beijing_data.district_payment_ability.items():
            weights[district] = data["population"] / total
        return weights

    def _get_hourly_factor(self, hour: int) -> float:
        """根据小时获取时段需求系数"""
        for time_range, factor in self.hourly_demand_factors.items():
            if time_range == "other":
                continue
            parts = time_range.split("-")
            if len(parts) == 2:
                start, end = int(parts[0]), int(parts[1])
                if start <= hour <= end:
                    return float(factor)
        return float(self.hourly_demand_factors.get("other", 1.0))

    def generate_daily_orders(self, day: int) -> List[Order]:
        """生成当日订单需求 - 多渠道"""
        all_orders = []

        # 1. 滴滴 App 推荐渠道
        app_orders = self._generate_channel_orders(
            self.beijing_data.acquisition_channels[0], day
        )
        all_orders.extend(app_orders)

        # 2. 医院驻点推广渠道
        station_orders = self._generate_station_orders(
            self.beijing_data.acquisition_channels[1], day
        )
        all_orders.extend(station_orders)

        # 3. 社区推广渠道
        community_orders = self._generate_community_orders(
            self.beijing_data.acquisition_channels[2], day
        )
        all_orders.extend(community_orders)

        # 4. 口碑传播渠道（基于已有用户）
        referral_orders = self._generate_referral_orders(day)
        all_orders.extend(referral_orders)

        # 5. 复购订单
        repurchase_orders = self._generate_repurchase_orders(day)
        all_orders.extend(repurchase_orders)

        # 6. 应用季节性因素
        all_orders = self._apply_seasonal_factor(all_orders, day)

        # 6.5 周内差异（周末需求下降20%）和月内差异（月末就医高峰+15%）
        day_of_week = day % 7
        weekend_factor = 0.8 if day_of_week in [5, 6] else 1.0
        day_of_month = (day % 30) + 1
        month_end_factor = 1.15 if day_of_month >= 25 else 1.0
        time_factor = weekend_factor * month_end_factor
        if time_factor != 1.0:
            target_count = max(0, int(len(all_orders) * time_factor))
            if target_count < len(all_orders):
                all_orders = random.sample(all_orders, target_count)
            elif target_count > len(all_orders) and all_orders:
                extra = target_count - len(all_orders)
                for _ in range(extra):
                    template = random.choice(all_orders)
                    new_order = Order(
                        user=template.user,
                        price=template.price,
                        created_at=template.created_at,
                    )
                    all_orders.append(new_order)

        # 7. 应用时段需求系数并记录 hour_of_day
        all_orders = self._apply_hourly_factors(all_orders)

        return all_orders

    def _apply_hourly_factors(self, orders: List[Order]) -> List[Order]:
        """为订单分配时段并应用需求系数"""
        if not self.hourly_demand_factors:
            return orders

        work_start, work_end = self.config.work_hours
        adjusted_orders: List[Order] = []

        for order in orders:
            # 随机分配一个工作时间内的小时
            hour = random.randint(work_start, work_end - 1)
            order.hour_of_day = hour

            # 根据时段系数决定是否保留该订单
            factor = self._get_hourly_factor(hour)
            if random.random() < factor / 1.8:  # 归一化到最大系数
                adjusted_orders.append(order)

        return adjusted_orders

    def _generate_channel_orders(self, channel: Dict, day: int) -> List[Order]:
        """生成特定渠道的订单"""
        # 计算该渠道的订单量
        exposure = channel["daily_exposure"]
        click_rate = channel["click_rate"]
        conversion_rate = channel["conversion_rate"]

        # 添加随机波动
        volatility = np.random.normal(0, 0.15)
        order_count = int(exposure * click_rate * conversion_rate * (1 + volatility))
        order_count = max(0, order_count)

        orders = []
        for _ in range(order_count):
            user = self._create_user_with_real_data(channel_type=channel["type"])
            order = self._create_order_with_real_pricing(user, day, channel)
            orders.append(order)

        return orders

    def _generate_station_orders(self, channel: Dict, day: int) -> List[Order]:
        """生成医院驻点推广订单"""
        if not self.beijing_data.station_promotion["enabled"]:
            return []

        orders = []
        target_hospitals = channel.get("hospitals", [])

        for hospital_name in target_hospitals:
            # 每个驻点医院的订单量
            exposure = channel["daily_exposure"]
            click_rate = channel["click_rate"]
            conversion_rate = channel["conversion_rate"]

            order_count = int(exposure * click_rate * conversion_rate)

            for _ in range(order_count):
                user = self._create_user_with_real_data(
                    channel_type="offline",
                    preferred_hospital=hospital_name
                )
                order = self._create_order_with_real_pricing(user, day, channel)
                orders.append(order)

        return orders

    def _generate_community_orders(self, channel: Dict, day: int) -> List[Order]:
        """生成社区推广订单"""
        target_districts = channel.get("target_districts", [])

        orders = []
        for district in target_districts:
            # 每个区域的订单量
            exposure = channel["daily_exposure"] / len(target_districts)
            click_rate = channel["click_rate"]
            conversion_rate = channel["conversion_rate"]

            order_count = int(exposure * click_rate * conversion_rate)

            for _ in range(order_count):
                user = self._create_user_with_real_data(
                    channel_type="offline",
                    district=district
                )
                order = self._create_order_with_real_pricing(user, day, channel)
                orders.append(order)

        return orders

    def _generate_referral_orders(self, day: int) -> List[Order]:
        """生成口碑传播订单"""
        # 基于高评分用户的推荐
        high_rating_users = [
            user for user in self.repurchase_pool.values()
            if user.last_escort_rating is not None and user.last_escort_rating >= 4.5
        ]

        orders = []
        for user in high_rating_users:
            # 每个高评分用户有 5% 概率推荐新用户
            if random.random() < 0.05:
                new_user = self._create_user_with_real_data(
                    channel_type="referral",
                    referrer=user
                )
                channel = self.beijing_data.acquisition_channels[3]
                order = self._create_order_with_real_pricing(new_user, day, channel)
                orders.append(order)

        return orders

    def _generate_repurchase_orders(self, day: int) -> List[Order]:
        """生成复购订单"""
        orders = []

        for _, user in list(self.repurchase_pool.items()):
            if day % self.config.repurchase_cycle_days == 0:
                # 根据用户收入等级决定复购概率
                repurchase_prob = self._get_repurchase_prob_by_income(user)

                if random.random() < repurchase_prob:
                    user.is_repurchase = True
                    user.total_orders += 1
                    order = self._create_order_with_real_pricing(user, day, None)
                    orders.append(order)

        return orders

    def _create_user_with_real_data(
        self,
        channel_type: str = "online",
        preferred_hospital: Optional[str] = None,
        district: Optional[str] = None,
        referrer: Optional[User] = None  # noqa: ARG002
    ) -> User:
        """创建用户 - 基于真实数据 + 年龄分层"""

        # 1. 生成用户年龄（60-90岁，正态分布偏向前高龄）
        age = _generate_user_age()
        age_group = _get_age_group(age)
        behavior = AGE_BEHAVIOR[age_group]

        # 2. 根据年龄分层确定子女代购率
        is_children_purchase = random.random() < behavior["children_purchase_rate"]

        # 3. 选择医院（基于权重）
        if preferred_hospital:
            target_hospital = preferred_hospital
        else:
            hospitals = list(self.hospital_weights.keys())
            weights = list(self.hospital_weights.values())
            target_hospital = random.choices(hospitals, weights=weights)[0]

        # 4. 选择疾病（基于真实分布）
        diseases = list(self.beijing_data.disease_distribution.keys())
        weights = list(self.beijing_data.disease_distribution.values())
        disease_type = random.choices(diseases, weights=weights)[0]

        # 5. 选择区域（影响付费能力）
        if district:
            user_district = district
        else:
            districts = list(self.district_weights.keys())
            weights = list(self.district_weights.values())
            user_district = random.choices(districts, weights=weights)[0]

        # 6. 确定收入等级
        income_levels = list(self.beijing_data.elderly_income_distribution.keys())
        income_ratios = [
            data["ratio"]
            for data in self.beijing_data.elderly_income_distribution.values()
        ]
        income_level = random.choices(income_levels, weights=income_ratios)[0]

        # 7. 创建用户（使用年龄分层后的配置）
        user = User(
            target_hospital=target_hospital,
            disease_type=disease_type,
            service_period=random.choice(["上午", "下午", "全天"]),
            price_sensitivity=behavior["price_sensitivity"],
            is_repurchase=False,
            total_orders=1,
            location_district=user_district,
            income_level=income_level,
            channel_type=channel_type,
            is_children_purchase=is_children_purchase,
            age=age,
            is_app_capable=behavior["is_app_capable"],
        )

        return user

    def _create_order_with_real_pricing(
        self,
        user: User,
        day: int,
        channel: Optional[Dict] = None
    ) -> Order:
        """创建订单 - 基于真实定价（动态定价）"""

        # 1. 基础价格（根据医院等级）
        hospital_tier = self._get_hospital_tier(user.target_hospital)
        base_price = self._get_base_price_by_hospital_tier(hospital_tier)

        # 2. 区域调整（付费能力）
        district_data = self.beijing_data.district_payment_ability.get(
            user.location_district
        )
        price_multiplier = district_data.get("price_multiplier", 1.0) if district_data else 1.0

        # 3. 时间段调整（高峰期加价）
        time_multiplier = self._get_time_multiplier(user.service_period)

        # 4. 疾病类型调整（复杂度）
        disease_multiplier = self._get_disease_multiplier(user.disease_type)

        # 5. 收入等级约束
        income_data = self.beijing_data.elderly_income_distribution.get(
            getattr(user, 'income_level', '中等收入')
        )
        max_price = income_data.get("max_price", 250) if income_data else 250

        # 6. 计算最终价格
        price = base_price * price_multiplier * time_multiplier * disease_multiplier

        # 7. 添加随机波动（±10%）
        volatility = np.random.uniform(-0.1, 0.1)
        price = price * (1 + volatility)
        price = max(80, price)  # 最低价格 80 元

        # 8. 价格超预算检查：超过用户最高接受价格则订单流失
        if price > max_price:
            order = Order(
                user=user,
                price=round(price, 2),
                created_at=datetime.now() + timedelta(days=day),
            )
            order.status = OrderStatus.CANCELLED
            order.cancel_reason = "价格超预算"
            if channel:
                order.acquisition_channel = channel["name"]
                order.acquisition_cost = channel.get("cost_per_order", 0)
            return order

        order = Order(
            user=user,
            price=round(price, 2),
            created_at=datetime.now() + timedelta(days=day),
        )

        # 存储渠道信息
        if channel:
            order.acquisition_channel = channel["name"]
            order.acquisition_cost = channel.get("cost_per_order", 0)

        return order

    def _get_hospital_tier(self, hospital_name: str) -> str:
        """获取医院等级"""
        for hospital in self.beijing_data.hospitals:
            if hospital["name"] == hospital_name:
                return hospital["tier"]
        return "medium"

    def _get_base_price_by_hospital_tier(self, tier: str) -> float:
        """根据医院等级获取基础价格"""
        tier_prices = {
            "top": 280,      # 顶级三甲（协和、301、北医三院）
            "large": 220,    # 大型三甲
            "medium": 180,   # 中型三甲
        }
        return tier_prices.get(tier, 200)

    def _get_time_multiplier(self, service_period: str) -> float:
        """获取时间段价格倍数"""
        time_multipliers = {
            "上午": 1.2,   # 上午高峰期（8-12点）
            "下午": 1.0,   # 下午正常
            "全天": 1.5,   # 全天服务加价
        }
        return time_multipliers.get(service_period, 1.0)

    def _get_disease_multiplier(self, disease_type: str) -> float:
        """获取疾病类型价格倍数（复杂度）"""
        disease_multipliers = {
            "心脏病": 1.3,      # 复杂，需要更专业的陪诊
            "糖尿病": 1.1,      # 中等复杂度
            "高血压": 1.0,      # 常见，相对简单
            "骨科疾病": 1.2,    # 需要搀扶等体力支持
            "呼吸系统": 1.1,    # 中等复杂度
            "消化系统": 1.0,    # 相对简单
            "其他": 1.0,        # 默认
        }
        return disease_multipliers.get(disease_type, 1.0)

    def _calculate_price_sensitivity(self, district: str, income_level: str) -> float:
        """计算价格敏感度"""
        # 高收入区域 + 高收入人群 = 低敏感度
        district_data = self.beijing_data.district_payment_ability.get(district, {})
        district_level = district_data.get("income_level", "medium")

        sensitivity_map = {
            ("high", "高收入"): 0.2,
            ("high", "中等收入"): 0.4,
            ("high", "低收入"): 0.6,
            ("medium", "高收入"): 0.3,
            ("medium", "中等收入"): 0.5,
            ("medium", "低收入"): 0.7,
            ("low", "高收入"): 0.4,
            ("low", "中等收入"): 0.6,
            ("low", "低收入"): 0.8,
        }

        return sensitivity_map.get((district_level, income_level), 0.5)

    def _get_repurchase_prob_by_income(self, user: User) -> float:
        """根据收入等级获取复购概率"""
        income_level = getattr(user, 'income_level', '中等收入')
        income_data = self.beijing_data.elderly_income_distribution.get(income_level, {})
        return income_data.get("repurchase_prob", 0.30)

    def _apply_seasonal_factor(self, orders: List[Order], day: int) -> List[Order]:
        """应用季节性因素"""
        # 简化：根据天数判断季节
        month = (day % 365) // 30 + 1

        if 3 <= month <= 5:
            season = "春季"
        elif 6 <= month <= 8:
            season = "夏季"
        elif 9 <= month <= 11:
            season = "秋季"
        else:
            season = "冬季"

        factor = self.beijing_data.seasonal_factors.get(season, 1.0)

        # 根据季节因子调整订单数量
        if factor > 1.0:
            # 增加订单
            additional = int(len(orders) * (factor - 1.0))
            for _ in range(additional):
                # 复制一个随机订单
                if orders:
                    template = random.choice(orders)
                    new_order = Order(
                        user=template.user,
                        price=template.price,
                        created_at=template.created_at,
                    )
                    orders.append(new_order)
        elif factor < 1.0:
            # 减少订单
            keep_count = int(len(orders) * factor)
            orders = random.sample(orders, keep_count)

        return orders

    def add_to_repurchase_pool(self, user: User, rating: Optional[float] = None):
        """将用户加入复购池"""
        if rating is not None:
            user.last_escort_rating = rating
        self.repurchase_pool[user.id] = user
