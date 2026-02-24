"""
基础版模拟引擎
"""
from typing import List, Dict, Any

from .base import BaseSimulation
from ..config.settings import SimulationConfig
from ..modules.demand import DemandGenerator
from ..modules.supply import SupplySimulator
from ..modules.matching import MatchingEngine
from ..modules.complaint_handler import ComplaintHandler
from ..modules.geo_matcher import GeoMatcher
from ..modules.referral_system import ReferralSystem
from ..models.entities import Order, Escort


class Simulation(BaseSimulation):
    """基础版沙盘模拟引擎"""

    def _init_modules(self):
        """初始化基础模块"""
        self._current_day = 0  # 供 _update_repurchase_pool 使用

        self.complaint_handler = ComplaintHandler()
        self.geo_matcher = GeoMatcher()
        self.referral_system = ReferralSystem()

        self.demand_gen = DemandGenerator(self.config)
        self.supply_sim = SupplySimulator(self.config)
        self.matching_engine = MatchingEngine(
            self.config,
            complaint_handler=self.complaint_handler,
            geo_matcher=self.geo_matcher,
        )

    def _update_supply(self, day: int):
        """更新供给状态"""
        self.supply_sim.daily_update(day)

    def _generate_demand(self, day: int) -> List[Order]:
        """生成需求"""
        return self.demand_gen.generate_daily_orders(day)

    def _get_available_escorts(self) -> List[Escort]:
        """获取可用陪诊员"""
        return self.supply_sim.get_available_escorts()

    def _process_matching(self, orders: List[Order], escorts: List[Escort], day: int):
        """处理订单匹配，并同步当日 day 供后续步骤使用"""
        self._current_day = day
        self.matching_engine.process_orders(orders, escorts, day)

    def _update_repurchase_pool(self):
        """更新复购池，并处理 NPS 分类与推荐"""
        for order in self.matching_engine.completed_orders:
            if order.is_success and order.rating and order.rating >= 4.0:
                self.demand_gen.add_to_repurchase_pool(order.user)

            if order.rating:
                self.referral_system.classify_user_nps(order.user.id, order.rating, order.user.is_children_purchase)
                self.referral_system.simulate_referral(order.user.id, self._current_day)

    def _record_daily_metrics(self, day: int, new_orders: List[Order]):
        """记录每日指标，并处理投诉率更新"""
        # 处理投诉并同步转化率修正系数
        self.complaint_handler.process_daily_complaints(day, len(new_orders))
        self.demand_gen.set_conversion_rate_modifier(
            self.complaint_handler.conversion_rate_modifier
        )

        demand_stats = {
            "new_orders": len([o for o in new_orders if not o.user.is_repurchase]),
            "repurchase_orders": len([o for o in new_orders if o.user.is_repurchase]),
            "total_orders": len(new_orders),
        }

        supply_stats = self.supply_sim.get_statistics()
        supply_stats["daily_recruit_cost"] = 0

        matching_stats = self.matching_engine.get_statistics()
        matching_stats["completed_orders_list"] = self.matching_engine.completed_orders

        self.analytics.record_daily(day, demand_stats, supply_stats, matching_stats, self.config)

    def _reset_daily_state(self):
        """重置每日状态"""
        self.matching_engine.reset_daily_count()

    def _print_progress(self, day: int):
        """打印进度"""
        stats = self.matching_engine.get_statistics()
        self.console.print(
            f"第 {day} 天 | "
            f"订单: {stats['completed_orders']} | "
            f"完成率: {stats['completion_rate']:.1%}"
        )
