# ============================================================================
# 增强版匹配引擎 - 尚未集成到主流程
# 基础版见 matching.py（当前主版本，被 simulation/simulation.py 使用）
# 版本关系：matching.py 是 v1.0（指定陪诊师优先），本文件是 v2.0（+地理距离+时间约束）
# 集成方式：未来可在 simulation/ 下新建 EnhancedSimulation 子类使用本模块
# ============================================================================
"""
增强版匹配引擎 - 支持地理距离和时间约束
"""
import random
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import numpy as np
import math

from ..config.settings import SimulationConfig
from ..config.beijing_real_data import BeijingRealDataConfig
from ..models.entities import Order, Escort, OrderStatus, EscortStatus


class EnhancedMatchingEngine:
    """增强版匹配引擎 - 考虑地理距离和时间约束"""

    def __init__(self, config: SimulationConfig, beijing_data: BeijingRealDataConfig):
        self.config = config
        self.beijing_data = beijing_data
        self.waiting_queue: List[Order] = []
        self.serving_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        self.failed_orders: List[Order] = []
        self._max_completed_records = 3000  # 内存保护：只保留最近3000条

        # 陪诊员当日接单计数
        self.daily_order_count: Dict[str, int] = {}

        # 陪诊员时间表（记录每个陪诊员的服务时间段）
        # 格式: {escort_id: [(day, start_hour, end_hour), ...]}
        self.escort_schedule: Dict[str, List[Tuple[int, float, float]]] = {}

        # 医院位置缓存
        self.hospital_locations = self._build_hospital_location_cache()

        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

    def _build_hospital_location_cache(self) -> Dict[str, Dict]:
        """构建医院位置缓存"""
        cache = {}
        for hospital in self.beijing_data.hospitals:
            cache[hospital["name"]] = {
                "lat": hospital["lat"],
                "lon": hospital["lon"],
                "district": hospital["district"],
            }
        return cache

    def process_orders(self, new_orders: List[Order], available_escorts: List[Escort], day: int):
        """处理订单匹配与履约"""
        # 1. 将新订单加入等待队列
        self.waiting_queue.extend(new_orders)

        # 2. 尝试匹配等待中的订单
        self._match_orders_with_constraints(available_escorts, day)

        # 3. 处理服务中的订单（模拟服务完成）
        self._process_serving_orders(day)

        # 4. 处理超时订单
        self._process_timeout_orders(day)

    def _match_orders_with_constraints(self, available_escorts: List[Escort], day: int):
        """匹配订单与陪诊员 - 考虑地理距离和时间约束"""
        matched_orders = []

        for order in self.waiting_queue[:]:  # 使用切片避免修改迭代中的列表
            # 查找可用的陪诊员（考虑地理距离和时间）
            escort = self._find_best_escort_with_constraints(order, available_escorts, day)

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

                # 更新陪诊员时间表
                if escort.id not in self.escort_schedule:
                    self.escort_schedule[escort.id] = []
                service_start_hour = self.config.work_hours[0]  # 使用工作时间窗口起始
                service_end_hour = service_start_hour + order.service_duration
                self.escort_schedule[escort.id].append((day, service_start_hour, service_end_hour))

                # 更新陪诊员接单计数
                self.daily_order_count[escort.id] = self.daily_order_count.get(escort.id, 0) + 1

                # 移到服务中列表
                self.serving_orders.append(order)
                matched_orders.append(order)

                # 如果达到日接单上限，从可用列表移除
                if self.daily_order_count[escort.id] >= self.config.daily_order_limit:
                    if escort in available_escorts:
                        available_escorts.remove(escort)

        # 从等待队列移除已匹配订单
        for order in matched_orders:
            if order in self.waiting_queue:
                self.waiting_queue.remove(order)

    def _find_best_escort_with_constraints(
        self,
        order: Order,
        available_escorts: List[Escort],
        day: int
    ) -> Optional[Escort]:
        """为订单找到最佳陪诊员 - 考虑地理距离和时间约束"""
        if not available_escorts:
            return None

        # 获取医院位置
        hospital_location = self.hospital_locations.get(order.user.target_hospital)
        if not hospital_location:
            return None

        # 筛选符合条件的陪诊员
        candidates = []
        for escort in available_escorts:
            # 1. 检查是否达到日接单上限
            if self.daily_order_count.get(escort.id, 0) >= self.config.daily_order_limit:
                continue

            # 2. 检查地理距离（通勤时间不超过90分钟）
            distance = self._calculate_distance(
                escort.location_lat,
                escort.location_lon,
                hospital_location["lat"],
                hospital_location["lon"]
            )
            commute_time = self._estimate_commute_time(distance)
            if commute_time > 90:  # 超过90分钟
                continue

            # 3. 检查时间冲突
            if self._has_time_conflict(escort.id, day):
                continue

            # 计算匹配分数
            score = self._calculate_match_score(escort, order, distance)
            candidates.append((escort, score, distance))

        if not candidates:
            return None

        # 按分数排序，选择最佳陪诊员
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点之间的距离（公里）- 使用 Haversine 公式"""
        R = 6371  # 地球半径（公里）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    def _estimate_commute_time(self, distance: float) -> float:
        """估算通勤时间（分钟）"""
        # 假设平均速度：
        # - 0-5公里：地铁/公交，20公里/小时
        # - 5-15公里：地铁，30公里/小时
        # - 15+公里：地铁+换乘，25公里/小时
        if distance <= 5:
            speed = 20
        elif distance <= 15:
            speed = 30
        else:
            speed = 25

        time_hours = distance / speed
        time_minutes = time_hours * 60
        return time_minutes

    def _has_time_conflict(self, escort_id: str, day: int, order_start_hour: int = 8, order_duration_hours: int = 3) -> bool:
        """检查陪诊师在指定时间段是否有冲突"""
        if escort_id not in self.escort_schedule:
            self.escort_schedule[escort_id] = []
            return False

        order_end_hour = order_start_hour + order_duration_hours
        for (scheduled_day, start_hour, end_hour) in self.escort_schedule[escort_id]:
            if scheduled_day == day:
                # 检查时间段重叠
                if not (order_end_hour <= start_hour or order_start_hour >= end_hour):
                    return True
        return False

    def _calculate_match_score(self, escort: Escort, order: Order, distance: float) -> float:
        """计算匹配分数"""
        score = 0.0

        # 1. 距离分数（距离越近分数越高，最高50分）
        distance_score = max(0, 50 - distance * 2)
        score += distance_score

        # 2. 评分分数（评分越高分数越高，最高30分）
        rating_score = escort.rating * 6  # 5分制 * 6 = 30分
        score += rating_score

        # 3. 专业度分数（擅长该医院，加20分）
        if order.user.target_hospital in escort.specialized_hospitals:
            score += 20

        return score

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

                self.failed_orders.append(order)

            completed.append(order)

        # 从服务中列表移除
        for order in completed:
            if order in self.serving_orders:
                self.serving_orders.remove(order)

    def _process_timeout_orders(self, day: int):
        """处理超时订单（等待过久的订单）"""
        timeout_orders = []

        for order in self.waiting_queue[:]:
            # 如果等待超过1天，标记为流失
            wait_time = (datetime.now() + timedelta(days=day)) - order.created_at
            if wait_time.days >= 1:
                order.status = OrderStatus.FAILED
                order.is_success = False
                order.cancel_reason = "等待超时，用户取消"
                self.failed_orders.append(order)
                timeout_orders.append(order)

        # 从等待队列移除
        for order in timeout_orders:
            if order in self.waiting_queue:
                self.waiting_queue.remove(order)

    def reset_daily_count(self):
        """重置每日接单计数"""
        self.daily_order_count.clear()
        # 清理过期的时间表记录
        # 保留最近7天的记录
        # 这里简化处理，实际应该根据日期清理

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
