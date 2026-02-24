# ============================================================================
# 基础版匹配引擎 - 当前主版本，被 simulation/simulation.py (v2.0) 使用
# 增强版见 matching_enhanced.py（支持地理距离和时间约束，尚未集成到主流程）
# ============================================================================
"""
匹配与履约模块 - 订单分配与服务完成
"""
import random
from typing import List, Optional, Dict, TYPE_CHECKING
from datetime import datetime, timedelta
import numpy as np

from ..config.settings import SimulationConfig
from ..models.entities import Order, Escort, OrderStatus, EscortStatus

if TYPE_CHECKING:
    from .complaint_handler import ComplaintHandler
    from .geo_matcher import GeoMatcher


class MatchingEngine:
    """匹配引擎 - 支持指定陪诊师优先匹配"""

    def __init__(self, config: SimulationConfig,
                 complaint_handler: Optional["ComplaintHandler"] = None,
                 geo_matcher: Optional["GeoMatcher"] = None):
        self.config = config
        self.complaint_handler = complaint_handler  # 投诉处理器（可选）
        self.geo_matcher = geo_matcher              # 地理位置匹配器（可选）
        self.waiting_queue: List[Order] = []
        self.serving_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        self.failed_orders: List[Order] = []
        self._max_completed_records = 3000  # 内存保护：只保留最近3000条（约30天x100单/天）

        # 陪诊员当日接单计数
        self.daily_order_count: Dict[str, int] = {}

        # 匹配统计
        self.match_statistics = {
            "designated_requests": 0,
            "designated_success": 0,
            "history_requests": 0,
            "history_success": 0,
            "normal_matches": 0,
        }

        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

    def process_orders(self, new_orders: List[Order], available_escorts: List[Escort], day: int):
        """处理订单匹配与履约"""
        # 1. 将新订单加入等待队列
        self.waiting_queue.extend(new_orders)

        # 2. 尝试匹配等待中的订单
        self._match_orders(available_escorts, day)

        # 3. 处理服务中的订单（模拟服务完成）
        self._process_serving_orders(day)

        # 4. 处理超时订单
        self._process_timeout_orders(day)

    def _match_orders(self, available_escorts: List[Escort], day: int):
        """匹配订单与陪诊员"""
        matched_orders = []

        for order in self.waiting_queue:
            # 查找可用的陪诊员
            escort = self._find_best_escort(order, available_escorts)

            if escort:
                # 匹配成功
                order.escort = escort
                order.status = OrderStatus.MATCHED
                order.matched_at = datetime.now() + timedelta(days=day)

                # 开始服务
                order.status = OrderStatus.SERVING
                order.service_start_at = order.matched_at
                escort.status = EscortStatus.SERVING
                escort.current_order_id = order.id

                # 生成服务时长
                order.service_duration = max(0.5, np.random.normal(
                    self.config.service_duration_mean,
                    self.config.service_duration_std
                ))

                # 更新陪诊员接单计数
                self.daily_order_count[escort.id] = self.daily_order_count.get(escort.id, 0) + 1

                # 移到服务中列表
                self.serving_orders.append(order)
                matched_orders.append(order)

                # 如果达到日接单上限，从可用列表移除
                if self.daily_order_count[escort.id] >= self.config.daily_order_limit:
                    available_escorts.remove(escort)

        # 从等待队列移除已匹配订单
        for order in matched_orders:
            self.waiting_queue.remove(order)

    def _find_best_escort(self, order: Order, available_escorts: List[Escort]) -> Optional[Escort]:
        """
        为订单找到最佳陪诊员 - 指定陪诊师优先匹配逻辑

        匹配优先级：
        1. 指定陪诊师（复购率82%）- 用户明确指定的陪诊师
        2. 历史陪诊师（复购率~50%）- 用户上次服务的陪诊师
        3. 普通匹配（复购率30%）- 擅长医院 + 评分高
        """
        if not available_escorts:
            order.cancel_reason = "陪诊师全满"
            return None

        # 筛选有效候选（未达接单上限、状态可用）
        candidates = [
            e for e in available_escorts
            if self.daily_order_count.get(e.id, 0) < self.config.daily_order_limit
            and e.rating >= 4.0  # 评分达标
        ]

        if not candidates:
            order.cancel_reason = "陪诊师全满"
            return None

        # 优先级1：指定陪诊师（复购率82%的关键杠杆）
        if order.user.has_designated_escort():
            self.match_statistics["designated_requests"] += 1
            designated_id = order.user.designated_escort_id
            designated = self._get_escort_by_id(designated_id, candidates) if designated_id else None
            if designated and self._is_escort_suitable(designated, order):
                order.match_type = "designated"
                order.is_designated_matched = True
                self.match_statistics["designated_success"] += 1
                return designated

        # 优先级2：历史陪诊师（复购用户）
        if order.user.has_history_escort():
            self.match_statistics["history_requests"] += 1
            last_id = order.user.last_escort_id
            history_escort = self._get_escort_by_id(last_id, candidates) if last_id else None
            if history_escort and self._is_escort_suitable(history_escort, order):
                order.match_type = "history"
                self.match_statistics["history_success"] += 1
                return history_escort

        # 优先级3：普通匹配（擅长医院 > 评分高）
        order.match_type = "normal"
        self.match_statistics["normal_matches"] += 1
        return self._normal_match(order, candidates)

    def _get_escort_by_id(self, escort_id: str, candidates: List[Escort]) -> Optional[Escort]:
        """根据ID从候选列表中获取陪诊员"""
        for escort in candidates:
            if escort.id == escort_id:
                return escort
        return None

    def _is_escort_suitable(self, escort: Escort, order: Order) -> bool:
        """检查陪诊员是否适合该订单"""
        # 检查评分是否达标
        if escort.rating < 4.0:
            return False

        # 检查日接单上限
        if self.daily_order_count.get(escort.id, 0) >= self.config.daily_order_limit:
            return False

        # 检查状态
        if escort.status != EscortStatus.AVAILABLE:
            return False

        return True

    def _normal_match(self, order: Order, candidates: List[Escort], max_distance_km: float = 15.0) -> Optional[Escort]:
        """普通匹配逻辑：地理位置优先 > 擅长医院 > 评分高"""
        # 如果有地理位置匹配器，优先使用距离最近的陪诊员
        if self.geo_matcher:
            result = self.geo_matcher.find_nearest_escort(order, candidates, max_distance_km=max_distance_km)
            if result.escort:
                if result.distance_km > max_distance_km:
                    # 距离超限，订单匹配失败
                    order.cancel_reason = "无附近陪诊师（距离超限）"
                    return None
                return result.escort

        # 回退：擅长该医院 > 评分高
        specialized = [
            e for e in candidates
            if order.user.target_hospital in e.specialized_hospitals
        ]

        if specialized:
            return max(specialized, key=lambda e: e.rating)
        else:
            return max(candidates, key=lambda e: e.rating)

    def _process_serving_orders(self, day: int):
        """处理服务中的订单"""
        completed = []

        for order in self.serving_orders:
            # 简化处理：假设订单在当天完成
            # 实际可以根据 service_duration 计算完成时间

            # 判定服务是否成功
            is_success = random.random() < self.config.service_success_rate

            if is_success:
                # 服务成功
                order.status = OrderStatus.COMPLETED
                order.is_success = True
                order.completed_at = datetime.now() + timedelta(days=day)

                # 生成用户评分
                order.rating = max(1.0, min(5.0, np.random.normal(
                    self.config.satisfaction_mean,
                    self.config.satisfaction_std
                )))

                # 更新陪诊员数据
                if order.escort:
                    order.escort.total_orders += 1
                    order.escort.total_income += order.price * self.config.escort_commission
                    # 更新陪诊员评分（简单平均）
                    order.escort.rating = (
                        (order.escort.rating * (order.escort.total_orders - 1) + order.rating)
                        / order.escort.total_orders
                    )
                    order.escort.status = EscortStatus.AVAILABLE
                    order.escort.current_order_id = None

                    # 更新用户历史陪诊师记录（新增）
                    order.user.add_history_escort(order.escort.id, order.rating)

                self.completed_orders.append(order)
                # 内存保护：截断超出上限的旧记录
                if len(self.completed_orders) > self._max_completed_records:
                    self.completed_orders = self.completed_orders[-self._max_completed_records:]
            else:
                # 服务失败
                order.status = OrderStatus.FAILED
                order.is_success = False
                order.cancel_reason = "服务过程中出现问题"

                if order.escort:
                    order.escort.status = EscortStatus.AVAILABLE
                    order.escort.current_order_id = None

                # 触发投诉处理（集成 complaint_handler）
                if self.complaint_handler:
                    self.complaint_handler.generate_complaint(
                        order_id=order.id,
                        user_id=order.user.id,
                        escort_id=order.escort.id if order.escort else None,
                        order_price=order.price,
                        day=day,
                    )

                self.failed_orders.append(order)

            completed.append(order)

        # 从服务中列表移除
        for order in completed:
            self.serving_orders.remove(order)

    def _process_timeout_orders(self, day: int):
        """处理超时订单：当日未匹配的订单标记为失败，并触发投诉"""
        timeout_orders = list(self.waiting_queue)

        for order in timeout_orders:
            order.status = OrderStatus.FAILED
            order.is_success = False
            order.cancel_reason = order.cancel_reason or "超时未匹配"

            # 匹配失败也可能触发投诉（用户等待过久）
            if self.complaint_handler:
                self.complaint_handler.generate_complaint(
                    order_id=order.id,
                    user_id=order.user.id,
                    escort_id=None,
                    order_price=order.price,
                    day=day,
                )

            self.failed_orders.append(order)

        self.waiting_queue.clear()

    def reset_daily_count(self):
        """重置每日接单计数"""
        self.daily_order_count.clear()

    def get_statistics(self) -> Dict:
        """获取履约统计数据"""
        total_orders = (
            len(self.completed_orders) +
            len(self.failed_orders) +
            len(self.serving_orders) +
            len(self.waiting_queue)
        )

        completed_count = len(self.completed_orders)
        failed_count = len(self.failed_orders)
        completion_rate = completed_count / total_orders if total_orders > 0 else 0

        avg_rating = np.mean([o.rating for o in self.completed_orders if o.rating]) \
            if self.completed_orders else 0

        avg_duration = np.mean([o.service_duration for o in self.completed_orders]) \
            if self.completed_orders else 0

        return {
            "total_orders": total_orders,
            "completed_orders": completed_count,
            "failed_orders": failed_count,
            "serving_orders": len(self.serving_orders),
            "waiting_orders": len(self.waiting_queue),
            "completion_rate": completion_rate,
            "avg_rating": avg_rating,
            "avg_duration": avg_duration,
        }
