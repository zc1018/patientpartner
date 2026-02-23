"""
地理位置匹配模块 - 基于北京市区域数据
实现就近匹配、跨区成本计算、供需不平衡模拟
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..models.entities import Escort, Order


# 北京主要区域中心坐标（经纬度）
BEIJING_DISTRICTS = {
    "朝阳": (39.9219, 116.4430),
    "海淀": (39.9601, 116.2980),
    "西城": (39.9122, 116.3628),
    "东城": (39.9289, 116.4173),
    "丰台": (39.8585, 116.2868),
    "石景山": (39.9146, 116.2219),
    "通州": (39.9023, 116.6572),
    "顺义": (40.1300, 116.6543),
    "昌平": (40.2207, 116.2312),
    "大兴": (39.7267, 116.3399),
    "房山": (39.7488, 116.1432),
    "门头沟": (39.9402, 116.1013),
    "平谷": (40.1408, 117.1121),
    "密云": (40.3763, 116.8430),
    "怀柔": (40.3162, 116.6378),
    "延庆": (40.4567, 115.9850),
}

# 区域类型（市区 vs 郊区）
URBAN_DISTRICTS = {"朝阳", "海淀", "西城", "东城", "丰台", "石景山"}
SUBURBAN_DISTRICTS = set(BEIJING_DISTRICTS.keys()) - URBAN_DISTRICTS

# 跨区通勤成本（元/单）
CROSS_DISTRICT_COST = 20.0

# 区域完成率差异
DISTRICT_COMPLETION_RATES = {
    "urban": 0.96,    # 市区完成率96%
    "suburban": 0.90, # 郊区完成率90%
}


@dataclass
class GeoMatchResult:
    """地理位置匹配结果"""
    escort: Optional[Escort]
    distance_km: float = 0.0
    is_cross_district: bool = False
    cross_district_cost: float = 0.0
    user_district: str = ""
    escort_district: str = ""
    is_urban: bool = True


class GeoMatcher:
    """
    地理位置匹配器

    基于北京市区域数据：
    - 市区需求70% / 陪诊员80%
    - 郊区需求30% / 陪诊员20%
    - 跨区通勤成本：¥20/单
    - 郊区完成率：90%（vs 市区96%）
    """

    def __init__(self):
        self.districts = BEIJING_DISTRICTS
        self.urban_districts = URBAN_DISTRICTS
        self.suburban_districts = SUBURBAN_DISTRICTS

    def find_nearest_escort(
        self,
        order: Order,
        candidates: List[Escort],
        max_distance_km: float = 15.0
    ) -> GeoMatchResult:
        """
        找到距离最近的可用陪诊员

        Args:
            order: 订单对象
            candidates: 候选陪诊员列表
            max_distance_km: 最大匹配距离（默认15公里）

        Returns:
            GeoMatchResult: 匹配结果
        """
        if not candidates:
            return GeoMatchResult(escort=None)

        user_lat = order.user.location_lat if hasattr(order.user, 'location_lat') else 39.9042
        user_lon = order.user.location_lon if hasattr(order.user, 'location_lon') else 116.4074
        user_district = self._get_district(user_lat, user_lon)

        best_escort = None
        best_distance = float('inf')
        best_result = None

        for escort in candidates:
            escort_lat = escort.location_lat
            escort_lon = escort.location_lon
            escort_district = escort.home_district

            distance = self._haversine_distance(
                user_lat, user_lon, escort_lat, escort_lon
            )

            if distance <= max_distance_km and distance < best_distance:
                best_distance = distance
                best_escort = escort
                is_cross = user_district != escort_district
                best_result = GeoMatchResult(
                    escort=escort,
                    distance_km=distance,
                    is_cross_district=is_cross,
                    cross_district_cost=CROSS_DISTRICT_COST if is_cross else 0.0,
                    user_district=user_district,
                    escort_district=escort_district,
                    is_urban=user_district in self.urban_districts,
                )

        if best_result is None:
            # 超出距离限制，选择最近的（允许跨区）
            for escort in candidates:
                distance = self._haversine_distance(
                    user_lat, user_lon, escort.location_lat, escort.location_lon
                )
                if distance < best_distance:
                    best_distance = distance
                    best_escort = escort
                    is_cross = user_district != escort.home_district
                    best_result = GeoMatchResult(
                        escort=escort,
                        distance_km=distance,
                        is_cross_district=is_cross,
                        cross_district_cost=CROSS_DISTRICT_COST if is_cross else 0.0,
                        user_district=user_district,
                        escort_district=escort.home_district,
                        is_urban=user_district in self.urban_districts,
                    )

        return best_result or GeoMatchResult(escort=None)

    def get_completion_rate_modifier(self, user_district: str) -> float:
        """
        根据区域获取完成率修正系数

        Args:
            user_district: 用户所在区域

        Returns:
            float: 完成率修正系数
        """
        if user_district in self.urban_districts:
            return DISTRICT_COMPLETION_RATES["urban"]
        return DISTRICT_COMPLETION_RATES["suburban"]

    def assign_user_location(self, user) -> tuple:
        """为用户分配地理位置（基于市区70%/郊区30%分布）"""
        if random.random() < 0.70:
            district = random.choice(list(self.urban_districts))
        else:
            district = random.choice(list(self.suburban_districts))

        base_lat, base_lon = self.districts[district]
        lat = base_lat + random.uniform(-0.05, 0.05)
        lon = base_lon + random.uniform(-0.05, 0.05)
        return lat, lon, district

    def assign_escort_location(self, escort) -> tuple:
        """为陪诊员分配地理位置（基于市区80%/郊区20%分布）"""
        if random.random() < 0.80:
            district = random.choice(list(self.urban_districts))
        else:
            district = random.choice(list(self.suburban_districts))

        base_lat, base_lon = self.districts[district]
        lat = base_lat + random.uniform(-0.05, 0.05)
        lon = base_lon + random.uniform(-0.05, 0.05)
        return lat, lon, district

    def get_supply_demand_balance(
        self,
        orders: List[Order],
        escorts: List[Escort]
    ) -> Dict[str, Dict]:
        """
        计算各区域供需平衡状况

        Returns:
            Dict: {区域: {需求数, 供给数, 平衡比}}
        """
        demand_by_district: Dict[str, int] = {}
        supply_by_district: Dict[str, int] = {}

        for order in orders:
            district = self._get_district(
                getattr(order.user, 'location_lat', 39.9042),
                getattr(order.user, 'location_lon', 116.4074)
            )
            demand_by_district[district] = demand_by_district.get(district, 0) + 1

        for escort in escorts:
            district = escort.home_district
            supply_by_district[district] = supply_by_district.get(district, 0) + 1

        result = {}
        all_districts = set(demand_by_district) | set(supply_by_district)
        for district in all_districts:
            demand = demand_by_district.get(district, 0)
            supply = supply_by_district.get(district, 0)
            result[district] = {
                "demand": demand,
                "supply": supply,
                "balance_ratio": supply / demand if demand > 0 else float('inf'),
                "is_urban": district in self.urban_districts,
            }

        return result

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间的球面距离（公里）"""
        R = 6371  # 地球半径（公里）
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    def _get_district(self, lat: float, lon: float) -> str:
        """根据坐标推断所在区域（找最近的区域中心）"""
        min_dist = float('inf')
        nearest = "朝阳"
        for district, (dlat, dlon) in self.districts.items():
            dist = self._haversine_distance(lat, lon, dlat, dlon)
            if dist < min_dist:
                min_dist = dist
                nearest = district
        return nearest
