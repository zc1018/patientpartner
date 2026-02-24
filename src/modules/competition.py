"""
竞争模拟模块 - 模拟市场竞争和份额变化

真实竞争格局：医院自营(40%) + 个人陪诊师(35%) + 滴滴(15%) + 其他平台(10%)
"""
import random
from typing import Dict, List
from dataclasses import dataclass, field
import numpy as np


# 真实竞争格局定义
REAL_COMPETITORS = {
    "hospital_self_operated": {
        "name": "医院自营陪诊",
        "market_share": 0.40,
        "price_range": (300, 500),
        "strengths": ["信任度高", "医院认可", "专业性强"],
        "weaknesses": ["价格贵", "预约难", "服务标准化差"],
        "target_users": "高端用户、复杂病症",
        "price_sensitivity": 0.2,  # 用户对价格不敏感
    },
    "individual_escorts": {
        "name": "个人陪诊师(微信群)",
        "market_share": 0.35,
        "price_range": (150, 200),
        "strengths": ["价格低", "灵活", "熟人推荐"],
        "weaknesses": ["不稳定", "无保障", "服务质量参差不齐"],
        "target_users": "价格敏感用户",
        "price_sensitivity": 1.5,
    },
    "didi_escort": {
        "name": "滴滴陪诊",
        "market_share": 0.15,
        "price_range": (220, 250),
        "strengths": ["平台保障", "标准化服务", "品牌信任"],
        "weaknesses": ["新进入者", "医院准入难"],
        "target_users": "中端用户、首次使用者",
        "price_sensitivity": 0.8,
    },
    "other_platforms": {
        "name": "其他平台",
        "market_share": 0.10,
        "price_range": (200, 280),
        "strengths": ["流量入口"],
        "weaknesses": ["非专业"],
        "target_users": "泛用户",
        "price_sensitivity": 1.0,
    }
}


@dataclass
class Competitor:
    """竞品模型"""
    name: str
    initial_market_share: float  # 初始市场份额
    current_market_share: float  # 当前市场份额

    # 竞争力指标
    avg_price: float  # 平均价格
    service_quality: float  # 服务质量（0-1）
    brand_strength: float  # 品牌力（0-1）

    # 运营数据
    total_orders: int = 0
    total_gmv: float = 0.0
    avg_rating: float = 4.5

    # 策略
    pricing_strategy: str = "stable"  # stable/aggressive/premium
    expansion_rate: float = 0.0  # 扩张速度

    # 真实竞争格局扩展字段
    price_range: tuple = (200, 300)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    target_users: str = ""
    price_sensitivity: float = 1.0


class CompetitionSimulator:
    """竞争模拟器"""

    def __init__(self, config):
        self.config = config

        # 初始化竞品
        self.competitors = self._initialize_competitors()

        # 市场总需求（基于滴滴流量）
        self.total_market_demand = self._calculate_total_market_demand()

        # 历史数据
        self.market_share_history: List[Dict] = []

        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

    def _initialize_competitors(self) -> Dict[str, Competitor]:
        """初始化竞品 - 真实竞争格局：医院自营 + 个人陪诊师 + 滴滴 + 其他平台"""
        competitors = {}
        for key, data in REAL_COMPETITORS.items():
            avg_price = sum(data["price_range"]) / 2
            # 根据竞争者类型设定服务质量和品牌力
            if key == "hospital_self_operated":
                quality, brand, strategy = 0.85, 0.90, "premium"
            elif key == "individual_escorts":
                quality, brand, strategy = 0.55, 0.30, "aggressive"
            elif key == "didi_escort":
                quality, brand, strategy = 0.75, 0.80, "stable"
            else:
                quality, brand, strategy = 0.60, 0.50, "stable"

            competitors[data["name"]] = Competitor(
                name=data["name"],
                initial_market_share=data["market_share"],
                current_market_share=data["market_share"],
                avg_price=avg_price,
                service_quality=quality,
                brand_strength=brand,
                pricing_strategy=strategy,
                price_range=tuple(data["price_range"]),
                strengths=data["strengths"],
                weaknesses=data["weaknesses"],
                target_users=data["target_users"],
                price_sensitivity=data["price_sensitivity"],
            )
        return competitors

    def _calculate_total_market_demand(self) -> int:
        """计算市场总需求"""
        # 基于滴滴流量漏斗，估算整个市场的需求
        # 假设滴滴占30%市场份额，反推总市场需求
        didi_daily_orders = (
            self.config.dau_base *
            self.config.exposure_rate *
            self.config.click_rate *
            self.config.consult_rate *
            self.config.order_rate
        )
        total_market_demand = didi_daily_orders / 0.15  # 滴滴占15%
        return int(total_market_demand)

    def simulate_competition(self, day: int, our_orders: int, our_avg_price: float, our_avg_rating: float):
        """模拟竞争 - 更新市场份额"""

        # 1. 更新我们的数据
        didi = self.competitors["滴滴陪诊"]
        didi.total_orders += our_orders
        didi.total_gmv += our_orders * our_avg_price
        didi.avg_price = our_avg_price
        didi.avg_rating = our_avg_rating

        # 2. 模拟竞品的运营数据
        self._simulate_competitor_operations(day)

        # 3. 计算竞争力得分
        competitiveness_scores = self._calculate_competitiveness_scores()

        # 4. 更新市场份额（基于竞争力）
        self._update_market_shares(competitiveness_scores)

        # 5. 记录历史数据
        self._record_market_share_history(day)

        # 6. 模拟价格战（如果有竞品采取激进策略）
        self._simulate_price_war(day)

    def _simulate_competitor_operations(self, day: int):
        """模拟竞品的运营数据"""
        for name, competitor in self.competitors.items():
            if name == "滴滴陪诊":
                continue  # 我们的数据已经更新

            # 根据市场份额估算订单量
            daily_orders = int(self.total_market_demand * competitor.current_market_share)

            # 添加随机波动
            daily_orders = int(daily_orders * np.random.uniform(0.8, 1.2))

            competitor.total_orders += daily_orders
            competitor.total_gmv += daily_orders * competitor.avg_price

            # 服务质量影响评分
            competitor.avg_rating = min(5.0, max(3.0,
                4.0 + competitor.service_quality * np.random.uniform(0.5, 1.0)
            ))

    def _calculate_competitiveness_scores(self) -> Dict[str, float]:
        """计算竞争力得分"""
        scores = {}

        for name, competitor in self.competitors.items():
            # 竞争力 = 价格竞争力 + 服务质量 + 品牌力

            # 1. 价格竞争力（价格越低越有竞争力，但不能太低）
            avg_market_price = np.mean([c.avg_price for c in self.competitors.values()])
            price_score = (avg_market_price - competitor.avg_price) / avg_market_price * 30
            price_score = max(-10, min(30, price_score))  # 限制在 -10 到 30 之间

            # 2. 服务质量得分
            quality_score = competitor.service_quality * 40

            # 3. 品牌力得分
            brand_score = competitor.brand_strength * 30

            # 总分
            total_score = price_score + quality_score + brand_score
            scores[name] = total_score

        return scores

    def _update_market_shares(self, competitiveness_scores: Dict[str, float]):
        """更新市场份额 - 基于竞争力得分"""

        # 1. 归一化得分（转换为市场份额）
        total_score = sum(competitiveness_scores.values())
        new_shares = {
            name: score / total_score
            for name, score in competitiveness_scores.items()
        }

        # 2. 平滑更新（避免剧烈波动）
        smoothing_factor = 0.1  # 每次只调整10%

        for name, competitor in self.competitors.items():
            old_share = competitor.current_market_share
            new_share = new_shares[name]

            # 平滑更新
            competitor.current_market_share = (
                old_share * (1 - smoothing_factor) +
                new_share * smoothing_factor
            )

    def _record_market_share_history(self, day: int):
        """记录市场份额历史"""
        record = {
            "day": day,
            "shares": {
                name: competitor.current_market_share
                for name, competitor in self.competitors.items()
            }
        }
        self.market_share_history.append(record)

    def _simulate_price_war(self, day: int):
        """模拟价格战"""
        # 如果有竞品采取激进策略，可能引发价格战
        aggressive_competitors = [
            c for c in self.competitors.values()
            if c.pricing_strategy == "aggressive"
        ]

        if aggressive_competitors and day % 10 == 0:  # 每10天检查一次
            # 降价 5-10%
            for competitor in aggressive_competitors:
                price_reduction = np.random.uniform(0.05, 0.10)
                competitor.avg_price *= (1 - price_reduction)
                competitor.avg_price = max(150, competitor.avg_price)  # 最低150元

    def get_our_market_share(self) -> float:
        """获取我们的市场份额"""
        return self.competitors["滴滴陪诊"].current_market_share

    def get_market_statistics(self) -> Dict:
        """获取市场统计数据"""
        return {
            "total_market_demand": self.total_market_demand,
            "our_market_share": self.get_our_market_share(),
            "competitors": {
                name: {
                    "market_share": c.current_market_share,
                    "avg_price": c.avg_price,
                    "avg_rating": c.avg_rating,
                    "total_orders": c.total_orders,
                }
                for name, c in self.competitors.items()
            }
        }

    def calculate_user_churn_to_competitors(self, our_failed_orders: int) -> int:
        """计算流失到竞品的用户数"""
        # 假设失败订单中有50%会流失到竞品
        churn_rate = 0.50
        churned_users = int(our_failed_orders * churn_rate)
        return churned_users

    def adjust_demand_by_competition(self, base_demand: int) -> int:
        """根据竞争调整需求"""
        # 根据我们的市场份额调整需求
        our_share = self.get_our_market_share()
        adjusted_demand = int(base_demand * our_share / 0.15)  # 基准是15%份额
        return adjusted_demand

    def simulate_escort_poaching(self, escorts: list, day: int) -> list:
        """模拟竞争对手挖走陪诊师"""
        if day % 30 != 0:  # 每月检查一次
            return []

        poached = []
        for escort in escorts:
            # 只有高评分陪诊师才会被挖
            if escort.rating >= 4.8:
                # 个人陪诊师市场（佣金更高）挖人概率
                poach_prob = 0.05  # 每月5%概率
                if random.random() < poach_prob:
                    poached.append(escort)
        return poached
